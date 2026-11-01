from collections.abc import Callable
from functools import partial

from lightshow.devices.moving_head.animations import (
    BernoulliLemniscateAnimation,
    BounceAnimation,
    CircleAnimation,
    RegularPolygonAnimation,
)
from lightshow.devices.moving_head.types import AbstractMHAnimation, FixtureCalibration

AnimationFactory = Callable[[FixtureCalibration], AbstractMHAnimation]


TRIANGLE_ANIMATION: AnimationFactory = partial(RegularPolygonAnimation, points_num=3)
SQUARE_ANIMATION: AnimationFactory = partial(RegularPolygonAnimation, points_num=4)
CIRCLE_ANIMATION: AnimationFactory = partial(CircleAnimation)
LEMNISCATE_ANIMATION: AnimationFactory = partial(BernoulliLemniscateAnimation)
BOUNCE_ANIMATION: AnimationFactory = partial(BounceAnimation)
