from collections import abc
from typing import Union, Iterator

from addict import Dict as Addict
from more_itertools import collapse

from instagram_is.streams import ThumbStream
from .models import InstagramPostThumb, InstagramComment, InstagramUser, InstagramPost
from .patches import CustomWebApiClient
from .tools import (
    _to_int,
    _get_caption,
    _timestamp_to_datetime,
    _to_bool,
    _get_hashtags,
    _get_mentions,
)


class WebApiClient:
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
    def node_to_post_thumb(cls, data: dict) -> InstagramPostThumb:
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
    def paginate_thumb_feed(
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
                yield cls.node_to_post_thumb(edge.node)

    @classmethod
    def post_info(cls, shortcode_or_model: Union[str, InstagramPost]) -> InstagramPost:
        if isinstance(shortcode_or_model, InstagramPost):
            return shortcode_or_model
        shortcode = shortcode_or_model
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
    def user_info(
        cls, username_or_user_id_or_model: Union[str, int, InstagramUser]
    ) -> InstagramUser:

        # todo: username <-> user_id bidict cache

        if isinstance(username_or_user_id_or_model, InstagramUser):
            return username_or_user_id_or_model

        if (
            not isinstance(username_or_user_id_or_model, str)
            or username_or_user_id_or_model.isdigit()
        ):
            user_id = _to_int(username_or_user_id_or_model)
            first_thumb = cls.user_feed(user_id).limit(1).to_list()[0]
            first_post = cls.post_info(first_thumb.shortcode)
            username_or_user_id_or_model = first_post.owner_username

        username = username_or_user_id_or_model

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


class LocationFeed(abc.Iterator):
    def __init__(self, *locations: Union[int, str, Iterator[Union[int, str]]]):
        location_ids = (_to_int(i) for i in collapse(locations))
        params = ({"location_id": i, "count": 50} for i in location_ids)
        media_path = ("data", "location", "edge_location_to_media")
        feeds = (
            WebApiClient.paginate_thumb_feed("location_feed", p, media_path)
            for p in params
        )
        self._stream = ThumbStream(*feeds)

    def __next__(self) -> InstagramPostThumb:
        return next(self._stream)


class UserFeed(abc.Iterator):
    def __next__(self) -> InstagramPostThumb:
        pass


class TagFeed(abc.Iterator):
    def __next__(self) -> InstagramPostThumb:
        pass


class SearchFeed(abc.Iterator):
    def __next__(self) -> InstagramPostThumb:
        pass


class Comments(abc.Iterator):
    # input a list of posts
    def __next__(self) -> InstagramComment:
        pass


class Users(abc.Iterator):
    def __next__(self) -> InstagramUser:
        pass


class Posts(abc.Iterator):
    def __next__(self) -> InstagramPost:
        pass
