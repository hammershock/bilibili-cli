"""Unit tests for WBI signature."""

import hashlib
from bilicli.wbi import _get_mixin_key, sign_params


def test_mixin_key_length():
    img_key = "a" * 32
    sub_key = "b" * 32
    key = _get_mixin_key(img_key, sub_key)
    assert len(key) == 32


def test_sign_params_adds_w_rid_and_wts():
    img_key = "7cd084941338484aae1ad9425b84077c"
    sub_key = "4932caff0ff746eab6f01bf08b70ac45"
    params = {"mid": 1, "token": "", "platform": "web", "web_location": 1550101}
    signed = sign_params(params, img_key, sub_key)
    assert "w_rid" in signed
    assert "wts" in signed
    assert len(signed["w_rid"]) == 32  # MD5 hex


def test_sign_params_strips_special_chars():
    img_key = "7cd084941338484aae1ad9425b84077c"
    sub_key = "4932caff0ff746eab6f01bf08b70ac45"
    params = {"foo": "bar!'()*"}
    signed = sign_params(params, img_key, sub_key)
    # Should not raise, and w_rid should be a valid md5
    assert len(signed["w_rid"]) == 32
