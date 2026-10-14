"""Tests for yi-hack camera capabilities and MQTT images."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components.camera import CameraEntityFeature
from homeassistant.components.ffmpeg import CONF_EXTRA_ARGUMENTS, DATA_FFMPEG
from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)

from custom_components.yi_hack.camera import YiHackCamera, YiHackMqttCamera
from custom_components.yi_hack.const import (
    ALLWINNERV2,
    CONF_HACK_NAME,
    CONF_MQTT_PREFIX,
    CONF_PTZ,
    CONF_TOPIC_MOTION_DETECTION_IMAGE,
)

from .conftest import add_config_entry


def _entry(hass):
    return add_config_entry(
        hass,
        title="camera",
        unique_id="b4:fb:e3:c0:1c:9f",
        data={
            CONF_HOST: "192.168.1.51",
            CONF_PORT: 80,
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
            CONF_NAME: "camera",
            CONF_MAC: "b4:fb:e3:c0:1c:9f",
            CONF_EXTRA_ARGUMENTS: "",
            CONF_HACK_NAME: ALLWINNERV2,
            CONF_PTZ: "no",
            CONF_MQTT_PREFIX: "camera",
            CONF_TOPIC_MOTION_DETECTION_IMAGE: "motion/image",
        },
    )


def test_camera_supported_features(hass) -> None:
    """Only the camera with a live stream advertises STREAM."""
    hass.data[DATA_FFMPEG] = Mock()
    entry = _entry(hass)

    assert YiHackCamera(hass, entry).supported_features == (
        CameraEntityFeature.STREAM | CameraEntityFeature.ON_OFF
    )
    assert (
        YiHackMqttCamera(hass, entry).supported_features == CameraEntityFeature.ON_OFF
    )


@pytest.mark.asyncio
async def test_mqtt_camera_returns_latest_image(hass) -> None:
    """The image remains unavailable until MQTT supplies the latest bytes."""
    camera = YiHackMqttCamera(hass, _entry(hass))
    camera.hass = hass
    assert await camera.async_camera_image() is None
    assert await camera.stream_source() is None

    with patch(
        "custom_components.yi_hack.camera.mqtt.async_subscribe", new_callable=AsyncMock
    ) as subscribe:
        await camera.async_added_to_hass()

    image_subscription = subscribe.call_args_list[1]
    assert image_subscription.args[1] == "camera/motion/image"
    assert image_subscription.args[3:] == (1, None)
    receive_image = image_subscription.args[2]
    for image in (b"\xff\xd8first\xff\xd9", b"\xff\xd8latest\xff\xd9"):
        receive_image(SimpleNamespace(payload=image))
        assert await camera.async_camera_image(width=320, height=180) == image
