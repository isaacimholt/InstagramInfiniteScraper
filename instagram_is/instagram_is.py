from typing import Iterator, Union

from addict import Dict as Addict
from more_itertools import collapse

from instagram_is.tools import (
    _to_int,
    _to_bool,
    _timestamp_to_datetime,
    _get_caption,
    _get_hashtags,
    _get_mentions,
)
from .models import InstagramPostThumb, InstagramUser, InstagramPost, InstagramComment
from .patches import CustomWebApiClient
from .streams import ThumbStream, UserStream, PostStream


class InstagramIS:
    def __init__(self, *args, **kwargs):
        params = dict(auto_patch=True)
        params.update(kwargs)
        self._web_api_client = CustomWebApiClient(*args, **params)

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

    def _paginate_thumb_feed(
        self, feed_name: str, feed_kwargs: dict, media_path: Iterator[str]
    ) -> Iterator[InstagramPostThumb]:
        has_next_page = True
        end_cursor = None
        while has_next_page:
            r = getattr(self._web_api_client, feed_name)(
                **feed_kwargs, end_cursor=end_cursor
            )
            media = Addict(r)
            for p in media_path:
                media = media[p]
            has_next_page = media.page_info.has_next_page
            end_cursor = media.page_info.end_cursor
            for edge in media.edges:
                yield self._node_to_post_thumb(edge.node)

    def tag_feed(
        self, *tags: Union[str, Iterator[str]]
    ) -> Iterator[InstagramPostThumb]:

        tags = collapse(tags)
        params = ({"tag": t, "count": 50} for t in tags)
        media_path = ("data", "hashtag", "edge_hashtag_to_media")
        feeds = (self._paginate_thumb_feed("tag_feed", p, media_path) for p in params)
        return ThumbStream(*feeds)

    def location_feed(
        self, *location_ids: Union[int, str, Iterator[Union[int, str]]]
    ) -> Iterator[InstagramPostThumb]:

        location_ids = collapse(location_ids)
        location_ids = (_to_int(i) for i in location_ids)
        params = ({"location_id": i, "count": 50} for i in location_ids)
        media_path = ("data", "location", "edge_location_to_media")
        feeds = (
            self._paginate_thumb_feed("location_feed", p, media_path) for p in params
        )
        return ThumbStream(*feeds)

    def user_feed(
        self, *user_ids_or_usernames: Union[int, str, Iterator[Union[int, str]]]
    ) -> Iterator[InstagramPostThumb]:
        # todo: better return type e.g. ThumbStream[InstagramPostThumb]
        """

        :param user_ids_or_usernames: note: passing a username will cause more url gets
        :return:
        """
        user_ids_or_usernames = collapse(user_ids_or_usernames)
        user_ids = (
            _to_int(i) or self._user_info(i).user_id for i in user_ids_or_usernames
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
        feeds = (self._paginate_thumb_feed("user_feed", p, media_path) for p in params)
        return ThumbStream(*feeds)

    def search_feed(self):
        # todo
        raise NotImplementedError

    def comment_feed(self):
        # todo
        raise NotImplementedError

    def _post_info(
        self, shortcode_or_model: Union[str, InstagramPost]
    ) -> InstagramPost:
        if isinstance(shortcode_or_model, InstagramPost):
            return shortcode_or_model
        shortcode = shortcode_or_model

        d = Addict(self._web_api_client.media_info2(shortcode))
        return InstagramPost(
            post_num_id=d.id or None,  # todo: this is actually a str
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

    def _user_info(self, u: Union[str, int]) -> InstagramUser:
        """

        :param u: Prefer username (fewer gets)
        :return:
        """

        # todo: username <-> user_id bidict cache

        if not isinstance(u, str) or u.isdigit():
            # input is a user_id, and we have to
            user_id = _to_int(u)
            # todo: potential problem if user has no posts, how can we get username?
            user_id = _to_int(u)
            first_thumb = self.user_feed(user_id).limit(1).to_list()[0]
            first_post = self._post_info(first_thumb.shortcode)
            u = first_post.owner_username

        username = u

        d = Addict(self._web_api_client.user_info2(user_name=username))
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

    def user(
        self,
        u: Union[
            int, str, InstagramUser, InstagramPost, InstagramPostThumb, InstagramComment
        ],
    ) -> InstagramUser:
        """
        Return a user's data
        :param u: username, user_id, various models, etc
        :return: data about a single user
        """

        # Be conservative in what you do, be liberal in what you accept
        if isinstance(u, InstagramUser):
            return u
        if isinstance(u, InstagramPost):
            return self._user_info(u.owner_username)
        if isinstance(u, InstagramPostThumb):
            return self._user_info(u.owner_num_id)
        if isinstance(u, InstagramComment):
            # todo
            raise NotImplementedError
        return self._user_info(u)

    def users(
        self,
        *u: Union[int, str, InstagramUser, Iterator[Union[int, str, InstagramUser]]]
    ) -> Iterator[InstagramUser]:
        """
        Return a stream of user data from a stream of users
        :param u: usernames, user_ids, various models, Iterators, etc
        :return: a stream of data about the input users
        """
        u = collapse(u, base_type=InstagramUser)
        return UserStream(self.user(i) for i in u)

    def post(
        self, p: Union[int, str, InstagramPost, InstagramPostThumb, InstagramComment]
    ) -> InstagramPost:
        """
        Return a post's data
        :param p: post shortcode, post_id, various models, etc
        :return: data about a single post
        """

        # Be conservative in what you do, be liberal in what you accept
        if isinstance(p, InstagramPost):
            return p
        if isinstance(p, InstagramPostThumb):
            return self._post_info(p.shortcode)
        if isinstance(p, InstagramComment):
            # todo
            raise NotImplemented
        return self._post_info(p)

    def posts(
        self,
        *p: Union[
            int,
            str,
            InstagramPost,
            InstagramPostThumb,
            InstagramComment,
            Iterator[
                Union[int, str, InstagramPost, InstagramPostThumb, InstagramComment]
            ],
        ]
    ) -> Iterator[InstagramPost]:
        """
        Return a stream of post data from a stream of posts
        :param p: post shortcodes, post_ids, various models, Iterators, etc
        :return: a stream of data about the input posts
        """
        p = collapse(p, base_type=InstagramPost)
        return PostStream(self.post(s) for s in p)

    def comments(
        self,
        *c: Union[
            int,
            str,
            InstagramPost,
            InstagramPostThumb,
            InstagramComment,
            Iterator[
                Union[int, str, InstagramPost, InstagramPostThumb, InstagramComment]
            ],
        ]
    ) -> Iterator[InstagramComment]:
        c = collapse(c, base_type=InstagramComment)
        # todo: logic to get comments from a post/post-like obj
        raise NotImplementedError

    def followed_by(self) -> Iterator[str]:
        """
        Who is following this user
        :return:
        """
        raise NotImplementedError

    def following(self) -> Iterator[str]:
        """
        Who is this user following
        :return:
        """
        raise NotImplementedError
    def likers(self) -> Iterator[str]:
        """
        Who liked this post
        :return:
        """
        raise NotImplementedError