"""DinHot holography engine: the canonical Python core (physics, numerics, metrics) and the method registry.

``core`` holds the forward models, metrics, device model, Zernike basis, trap physics, particle dynamics, the emulated
camera and the portable RNG; ``methods`` holds the hologram methods (registered by the method units). The live lane
of the web app is a TypeScript port held by parity tests against fixtures this engine writes (ADR-0054).
"""
