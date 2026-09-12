"""An explicit body decoder calibrated on descending-neuron responses."""
import numpy as np

STEPS = 32


def measure(brain, senses, direction=None, steps=STEPS, intensity=1.):
    brain.reset(64)
    counts = np.zeros(brain.n, np.float32)
    for _ in range(steps):
        eye = senses.vision(direction, intensity) if direction is not None else None
        counts[brain.step(eye_drive=eye)] += 1
    return counts


class MotorDecoder:
    def __init__(self, brain, senses):
        self.neurons = np.flatnonzero(brain.superclass == "descending_neuron")
        self.baseline = measure(brain, senses)
        conditions = [(d, intensity) for intensity in (.65, 1., 1.4) for d in np.linspace(-1, 1, 9)]
        responses = np.asarray([(measure(brain, senses, d, intensity=intensity) - self.baseline)[self.neurons]
                                for d, intensity in conditions])
        self.scale = np.maximum(np.linalg.norm(responses, axis=0), 1.)
        x = responses / self.scale
        # Known virtual visual stimuli calibrate only the body interface. These
        # are not job labels and neither geometry nor text enters decode().
        desired = np.asarray([(d, (.3 + .7 * (1 - abs(d))) * (1.5 - intensity),
                               (intensity - .65) / .75) for d, intensity in conditions])
        self.weights = x.T @ np.linalg.solve(x @ x.T + np.eye(len(x)) * .08, desired)
        predicted = x @ self.weights
        self.calibration = dict(responsiveNeurons=int(np.count_nonzero(np.abs(responses).sum(axis=0))),
                                trainingMAE=round(float(np.mean(np.abs(predicted - desired))), 4),
                                samples=len(conditions))

    def decode(self, counts, baseline=None):
        baseline = self.baseline if baseline is None else baseline
        x = (counts - baseline)[self.neurons] / self.scale
        output = x @ self.weights
        return float(np.clip(output[0], -1, 1)), float(np.clip(output[1], 0, 1)), float(np.clip(output[2], 0, 1))
