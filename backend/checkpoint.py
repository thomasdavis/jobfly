"""Portable array checkpoints. No pickle or executable deserialization."""
import base64
import numpy as np


def pack(value):
    if isinstance(value, np.ndarray):
        return {"__array__": base64.b64encode(value.tobytes()).decode(),
                "dtype": value.dtype.str, "shape": list(value.shape)}
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): pack(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [pack(v) for v in value]
    return value


def unpack(value):
    if isinstance(value, dict) and "__array__" in value:
        dtype = np.dtype(value["dtype"])
        if dtype.kind not in "biuf" or dtype.itemsize > 8:
            raise ValueError("Invalid checkpoint array type")
        return np.frombuffer(base64.b64decode(value["__array__"], validate=True), dtype).reshape(value["shape"]).copy()
    if isinstance(value, dict):
        return {k: unpack(v) for k, v in value.items()}
    if isinstance(value, list):
        return [unpack(v) for v in value]
    return value
