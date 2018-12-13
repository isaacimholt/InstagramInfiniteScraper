from typing import NamedTuple, Dict, Sequence

import pendulum


class InstagramPostThumb(NamedTuple):
    post_num_id: str
    owner_num_id: int
    caption: str
    shortcode: str
    comment_count: int
    like_count: int
    created_at: pendulum.datetime
    img_height: int
    img_width: int
    img_url: str
    is_video: bool
    hashtags: Sequence[str]
    mentions: Sequence[str]

    @property
    def simple_str(self):
        d = self.created_at.to_datetime_string()
        return f"{self.shortcode} {d} {self.caption[:30]}"

    @property
    def engagement(self):
        return self.like_count + self.comment_count


class InstagramPost(NamedTuple):
    post_num_id: int
    shortcode: str
    img_height: int
    img_width: int
    display_url: str
    is_video: bool
    caption_is_edited: bool
    created_at: pendulum.datetime
    like_count: int
    comment_count: int
    location_id: int
    location_name: str
    location_address_json: str
    owner_id: int
    owner_username: str
    owner_full_name: str
    is_ad: bool
    caption: str
    users_in_photo: Sequence[Dict[str, str]]
    hashtags: Sequence[str]
    mentions: Sequence[str]

    @property
    def simple_str(self):
        d = self.created_at.to_datetime_string()
        return f"{self.shortcode} {d} {self.caption[:30]}"

    @property
    def engagement(self):
        return self.like_count + self.comment_count


class InstagramUser(NamedTuple):
    biography: str
    website: str
    followed_by_count: int
    follows_count: int
    full_name: str
    user_id: int
    is_business_account: bool
    is_joined_recently: bool
    is_private: bool
    is_verified: bool
    profile_pic_url: str
    username: str
    connected_fb_page: str
    media_count: int


class InstagramComment(NamedTuple):
    # todo
    pass
