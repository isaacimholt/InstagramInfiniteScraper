import re
from typing import Iterator, Union, Sequence

import pendulum
from addict import Dict as Addict
from more_itertools import collapse

from .models import InstagramPostThumb, InstagramUser, InstagramPost
from .patches import CustomWebApiClient
from .streams import ThumbStream, UserStream, PostStream


class InstagramIS:
    __web_api_client = None

    @classmethod
    def _get_web_api_client(cls):
        """
        Prevent multiple instances of web api client
        """
        if cls.__web_api_client is None:
            # todo: cookies etc? See instagram private api readme for details
            cls.__web_api_client = CustomWebApiClient(auto_patch=True)
        return cls.__web_api_client

    @classmethod
    def _node_to_post_thumb(cls, data: dict) -> InstagramPostThumb:
        data = Addict(data)
        caption = _get_caption(data)
        return InstagramPostThumb(
            post_num_id=data.id,
            owner_num_id=_to_int(data.owner.id),
            caption=caption,
            shortcode=data.shortcode or None,
            comment_count=_to_int(data.edge_media_to_comment.count),
            like_count=_to_int(data.edge_media_preview_like.count),
            created_at=_timestamp_to_datetime(data.taken_at_timestamp),
            img_height=_to_int(data.dimensions.height),
            img_width=_to_int(data.dimensions.width),
            img_url=data.display_url or None,
            is_video=_to_bool(data.is_video),
            hashtags=_get_hashtags(caption),
            mentions=_get_mentions(caption),
        )

    @classmethod
    def tag_feed(cls, *tags: Union[str, Iterator[str]]) -> Iterator[InstagramPostThumb]:

        tags = collapse(tags)
        params = ({"tag": t, "count": 50} for t in tags)
        media_path = ("data", "hashtag", "edge_hashtag_to_media")
        feeds = (cls._paginate_thumb_feed("tag_feed", p, media_path) for p in params)
        return ThumbStream(feeds)

    @classmethod
    def location_feed(
        cls, *location_ids: Union[int, str, Iterator[Union[int, str]]]
    ) -> Iterator[InstagramPostThumb]:

        location_ids = collapse(location_ids)
        location_ids = (_to_int(i) for i in location_ids)
        params = ({"location_id": i, "count": 50} for i in location_ids)
        media_path = ("data", "location", "edge_location_to_media")
        feeds = (
            cls._paginate_thumb_feed("location_feed", p, media_path) for p in params
        )
        return ThumbStream(feeds)

    @classmethod
    def user_feed(
        cls, *user_ids_or_usernames: Union[int, str, Iterator[Union[int, str]]]
    ) -> Iterator[InstagramPostThumb]:
        # todo: better return type e.g. ThumbStream[InstagramPostThumb]
        """

        :param user_ids_or_usernames: note that passing a username will require an additional url get
        :return:
        """
        user_ids_or_usernames = collapse(user_ids_or_usernames)
        user_ids = (
            _to_int(i) or cls.user_info(i).user_id for i in user_ids_or_usernames
        )
        params = (
            {
                "user_id": i,
                "extract": False,  # True removes data like cursor
                "count": 50,
            }
            for i in user_ids
        )
        media_path = ("data", "user", "edge_owner_to_timeline_media")
        feeds = (cls._paginate_thumb_feed("user_feed", p, media_path) for p in params)
        return ThumbStream(feeds)

    @classmethod
    def _paginate_thumb_feed(
        cls, feed_name: str, feed_kwargs: dict, media_path: Iterator[str]
    ) -> Iterator[InstagramPostThumb]:
        web_api = cls._get_web_api_client()
        has_next_page = True
        end_cursor = None
        while has_next_page:
            r = getattr(web_api, feed_name)(**feed_kwargs, end_cursor=end_cursor)
            media = Addict(r)
            for p in media_path:
                media = media[p]
            has_next_page = media.page_info.has_next_page
            end_cursor = media.page_info.end_cursor
            for edge in media.edges:
                yield cls._node_to_post_thumb(edge.node)

    @classmethod
    def post_info(cls, shortcode: str) -> InstagramPost:
        web_api = cls._get_web_api_client()
        d = Addict(web_api.media_info2(shortcode))
        return InstagramPost(
            post_num_id=d.id or None,
            shortcode=d.shortcode or None,
            img_height=_to_int(d.dimensions.height),
            img_width=_to_int(d.dimensions.width),
            display_url=d.display_url or None,
            is_video=_to_bool(d.is_video),
            caption_is_edited=_to_bool(d.caption_is_edited),
            created_at=_timestamp_to_datetime(d.taken_at_timestamp),
            like_count=_to_int(d.likes.count),
            comment_count=_to_int(d.comments.count),
            location_id=_to_int(d.location and d.location.id),
            location_name=(d.location and d.location.name) or None,
            location_address_json=(d.location and d.location.address_json) or None,
            owner_id=_to_int(d.owner.id),
            owner_username=d.owner.username or None,
            owner_full_name=d.owner.full_name or None,
            is_ad=_to_bool(d.is_ad),
            caption=d.caption.text or None,
            users_in_photo=[p.user for p in d.users_in_photo],
            hashtags=_get_hashtags(d.caption.text),
            mentions=_get_mentions(d.caption.text),
        )

    @classmethod
    def post_stream(cls, shortcodes: Iterator[str]) -> Iterator[InstagramPost]:
        return PostStream(cls.post_info(shortcode) for shortcode in shortcodes)

    @classmethod
    def user_info(cls, username_or_user_id: Union[str, int]) -> InstagramUser:

        # todo: username <-> user_id bidict cache

        if not isinstance(username_or_user_id, str) or username_or_user_id.isdigit():
            user_id = _to_int(username_or_user_id)
            first_thumb = cls.user_feed(user_id).limit(1).to_list()[0]
            first_post = cls.post_info(first_thumb.shortcode)
            username_or_user_id = first_post.owner_username

        username = username_or_user_id

        web_api = cls._get_web_api_client()
        d = Addict(web_api.user_info2(user_name=username))
        return InstagramUser(
            biography=d.biography or None,
            website=d.website or None,
            followed_by_count=_to_int(d.counts.followed_by),
            follows_count=_to_int(d.counts.follows),
            full_name=d.full_name or None,
            user_id=_to_int(d.id),
            is_business_account=_to_bool(d.is_business_account),
            is_joined_recently=_to_bool(d.is_joined_recently),
            is_private=_to_bool(d.is_private),
            is_verified=_to_bool(d.is_verified),
            profile_pic_url=d.profile_pic_url or None,
            username=d.username or None,
            connected_fb_page=d.connected_fb_page or None,
            media_count=_to_int(d.counts.media),
        )

    @classmethod
    def user_stream(
        cls, *usernames_or_user_ids: Union[int, str, Iterator[Union[int, str]]]
    ) -> Iterator[InstagramUser]:
        usernames_or_user_ids = collapse(usernames_or_user_ids)
        users = (cls.user_info(i) for i in usernames_or_user_ids)
        return UserStream([users])


def _to_int(val, default=None) -> Union[int, None]:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _to_bool(val, default=None) -> Union[bool, None]:
    try:
        return bool(val)
    except (ValueError, TypeError):
        return default


def _timestamp_to_datetime(val, default=None) -> Union[pendulum.datetime, None]:
    try:
        return pendulum.from_timestamp(val)
    except (ValueError, TypeError):
        return default


def _get_caption(data):
    try:
        return data.edge_media_to_caption.edges[0].node.text or ""
    except IndexError:
        return ""


# https://gist.github.com/mahmoud/237eb20108b5805aed5f
_hashtag_re = re.compile("(?:^|\s)[＃#]{1}(\w+)", re.UNICODE)
_mention_re = re.compile("(?:^|\s)[＠@]{1}([^\s#<>[\]|{}]+)", re.UNICODE)


def _get_matches(text: str, pattern) -> Sequence[str]:
    """
    Returns sorted list of unique lower-cased items that match the regex
    :param text: any text
    :return: sorted list of unique lower-cased items
    """
    # todo: test hashtags ending with surrogate pair emojii (e.g. family, flags)
    try:
        # hashtags are case insensitive
        matches = set(s.lower() for s in pattern.findall(text))
    except TypeError:
        # https://stackoverflow.com/questions/43727583/expected-string-or-bytes-like-object
        matches = set()
    # sorted so that equality matching works when updating???
    return tuple(sorted(matches))


def _get_hashtags(text: str) -> Sequence[str]:
    return _get_matches(text, _hashtag_re)


def _get_mentions(text: str) -> Sequence[str]:
    return _get_matches(text, _mention_re)
