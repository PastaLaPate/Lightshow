from collections.abc import Callable
from functools import partial

from lightshow.devices.moving_head.animations import (
    BernoulliLemniscateAnimation,
    BounceAnimation,
    BreakCircleAnimation,
    CircleAnimation,
    RegularPolygonAnimation,
)
from lightshow.devices.moving_head.moving_head_animations import AMHAnimation
from lightshow.devices.moving_head.moving_head_colors import DEFAULT_RGBs
from lightshow.devices.types import FixtureCalibration

AnimationFactory = Callable[[FixtureCalibration], AMHAnimation]


TRIANGLE_ANIMATION: AnimationFactory = partial(
    RegularPolygonAnimation, rgb=DEFAULT_RGBs, points_num=3
)
SQUARE_ANIMATION: AnimationFactory = partial(
    RegularPolygonAnimation, rgb=DEFAULT_RGBs, points_num=4
)
CIRCLE_ANIMATION: AnimationFactory = partial(
    CircleAnimation, rgb=DEFAULT_RGBs, speed=0.3
)
LEMNISCATE_ANIMATION: AnimationFactory = partial(
    BernoulliLemniscateAnimation, rgb=DEFAULT_RGBs, speed=0.3
)
CIRCLE_BREAK_ANIMATION: AnimationFactory = partial(BreakCircleAnimation, hue_speed=0.5)
BOUNCE_ANIMATION: AnimationFactory = partial(BounceAnimation, rgb=DEFAULT_RGBs)
