"""Computer-vision inference infrastructure.

The application depends on the CVInferenceService interface (interface.py),
never on a concrete model file. The default implementation is a clearly
labelled development mock (mock_impl.py) that must never be presented as real
ML inference. A real backend (e.g. Keras/TensorFlow) plugs in behind the same
interface when the ML pipeline produces a validated checkpoint.
"""
