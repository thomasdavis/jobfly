"""Portable array checkpoints. No pickle or executable deserialization."""
import base64
import numpy as np


def pack(value):
    if isinstance(value, np.ndarray):
        stored = value
        # Spike-count arrays are exact small integers represented as floats.
        # Store them losslessly as bytes, retaining the original dtype on read.
        if value.size and value.dtype.kind in "fiu":
            low, high = value.min(), value.max()
            if low >= 0 and high <= 255:
                candidate = value.astype(np.uint8)
                signed_zero = value.dtype.kind == "f" and np.any(np.signbit(value) & (value == 0))
                if not signed_zero and np.array_equal(value, candidate):
                    stored = candidate
        return {"__array__": base64.b64encode(stored.tobytes()).decode(),
                "dtype": stored.dtype.str, "original_dtype": value.dtype.str, "shape": list(value.shape)}
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
        original = np.dtype(value.get("original_dtype", value["dtype"]))
        if original.kind not in "biuf" or original.itemsize > 8:
            raise ValueError("Invalid checkpoint original array type")
        return np.frombuffer(base64.b64decode(value["__array__"], validate=True), dtype).reshape(value["shape"]).astype(original, copy=True)
    if isinstance(value, dict):
        return {k: unpack(v) for k, v in value.items()}
    if isinstance(value, list):
        return [unpack(v) for v in value]
    return value
