"""
Complex number utility functions for holographic computations.

This module provides optimized complex number operations that mirror the
original C++ BasicComplex library used in the legacy DinHotSys application.
While Python's native complex type and NumPy handle most cases, these
utilities offer convenience wrappers with domain-specific semantics.

The original C++ code (BasicComplex.h/.cpp) implemented:
    - ExpImaginaria: exp(i * theta) = cos(theta) + i*sin(theta)
    - ExpImaginariaF: factor * exp(i * theta)
    - ArgumentoComplejo: atan2(imag, real) -- the phase angle
    - AbsolutoComplejo: sqrt(real^2 + imag^2) -- the magnitude

In this Python port, NumPy vectorized operations replace the manual
loop-based computations from the C++ code.
"""
import numpy as np
from typing import Union

# Type alias for array-like inputs
ArrayLike = Union[float, np.ndarray]


def exp_imaginary(theta: ArrayLike) -> Union[complex, np.ndarray]:
    """Compute exp(i * theta) = cos(theta) + i * sin(theta).

    This is the core operation in the Gerchberg-Saxton algorithm, used
    to convert phase values into complex phasors. Corresponds to the
    original C++ function ExpImaginaria().

    Args:
        theta: Phase angle(s) in radians. Can be a scalar or NumPy array.

    Returns:
        Complex phasor(s) on the unit circle.

    Examples:
        >>> exp_imaginary(0.0)
        (1+0j)
        >>> np.abs(exp_imaginary(np.pi/2) - 1j) < 1e-10
        True
    """
    return np.exp(1j * theta)


def exp_imaginary_scaled(theta: ArrayLike, factor: float) -> Union[complex, np.ndarray]:
    """Compute factor * exp(i * theta).

    Scaled complex exponential used when combining trap contributions
    with different amplitudes. Corresponds to the original C++ function
    ExpImaginariaF().

    Args:
        theta: Phase angle(s) in radians.
        factor: Scaling amplitude factor.

    Returns:
        Scaled complex phasor(s).
    """
    return factor * np.exp(1j * theta)


def complex_argument(z: Union[complex, np.ndarray]) -> ArrayLike:
    """Extract the phase angle (argument) of a complex number.

    Returns the angle in radians in the range (-pi, pi]. Corresponds
    to the original C++ function ArgumentoComplejo(), which used atan2.

    Args:
        z: Complex number(s).

    Returns:
        Phase angle(s) in radians.
    """
    return np.angle(z)


def complex_magnitude(z: Union[complex, np.ndarray]) -> ArrayLike:
    """Compute the magnitude (absolute value) of a complex number.

    Corresponds to the original C++ function AbsolutoComplejo(), which
    computed sqrt(real^2 + imag^2).

    Args:
        z: Complex number(s).

    Returns:
        Magnitude(s) as real value(s).
    """
    return np.abs(z)


def normalize_phase(phi: np.ndarray) -> np.ndarray:
    """Normalize phase values to the range [0, 2*pi).

    SLM devices require phase values in a specific range. This function
    wraps arbitrary phase values into [0, 2*pi) for display and device
    output.

    Args:
        phi: Phase array with arbitrary values.

    Returns:
        Phase array wrapped to [0, 2*pi).
    """
    return phi % (2 * np.pi)


def phase_to_grayscale(phi: np.ndarray) -> np.ndarray:
    """Convert phase values [0, 2*pi) to grayscale [0, 255].

    Maps the full 2*pi phase range linearly to 8-bit grayscale values
    for display on screen or sending to an SLM.

    Args:
        phi: Phase array in [0, 2*pi).

    Returns:
        Array of uint8 values in [0, 255].
    """
    normalized = normalize_phase(phi)
    return (normalized / (2 * np.pi) * 255).astype(np.uint8)


def compute_rho(coord_x: np.ndarray, coord_y: np.ndarray,
                trap_x: float, trap_y: float) -> np.ndarray:
    """Compute the dot-product matrix rho for a trap position.

    In the original C++ code, _rrho[i][j][k] stored the precomputed
    dot product between the SLM pixel coordinates and each trap position:
        rho = x_pixel * x_trap + y_pixel * y_trap

    This dot product appears in the phase kernel as:
        K_j(u,v) = phase_scale * rho(u,v)

    Since both the SLM coordinates and trap positions are normalized
    to [-1, 1], the rho values lie in [-2, 2]. When multiplied by
    phase_scale (typically pi), this gives phase contributions of
    O(1) radians -- the correct regime for the GS algorithm to converge.

    Args:
        coord_x: 2D array of normalized x-coordinates on the SLM plane.
        coord_y: 2D array of normalized y-coordinates on the SLM plane.
        trap_x: X position of the trap in normalized coordinates.
        trap_y: Y position of the trap in normalized coordinates.

    Returns:
        2D array of dot-product values in the range [-2, 2].
    """
    return coord_x * trap_x + coord_y * trap_y
