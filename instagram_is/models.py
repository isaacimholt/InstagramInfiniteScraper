from typing import NamedTuple, List, Dict

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
    hashtags: List[str]
    mentions: List[str]

    @property
    def simple_str(self):
        return f"{self.shortcode} {self.created_at.to_datetime_string()} {self.caption[:30]}"


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
    users_in_photo: List[Dict[str, str]]
    hashtags: List[str]
    mentions: List[str]


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