# What Jobfly can demonstrate

Jobfly is a connectome-based computational experiment with engineered job, sensory,
learning and body interfaces. It is not a validated simulation of a living fly,
evidence of fly cognition about careers, or a validated job recommender.

## Version 4 correction

Version 3 displayed 24 bodies taking turns through one reset network and one
learned readout. Those were not independent brains. Its elapsed clock counted
aggregate computation rather than equal time in 24 brains. Earlier screenshots
and verification records describe that implementation only.

Version 4 gives all 24 individuals private dynamical and learned state. Sharing
immutable anatomical constants is a memory representation, not state sharing.
Every world step advances every real brain by 20 ms. Resting does not stop the
brain. No runtime observation or reward resets its voltage or noise stream.
Disconnected sessions pause; returning restores their checkpoints.

Every stimulus measurement has a paired unstimulated control starting at exactly
the same voltage, spikes, weights and random-generator state. Both advance with
the same noise. Readouts use their activity difference, excluding directly
injected cells. The real individual's continuous state is never replaced by the
control state. The controls and any unfinished measurements are checkpointed too.

## Claims and acceptance checks

1. **Independence:** perturb one brain; all other voltages, spike histories, RNG
   states and synaptic factors remain unchanged. Common seeds and identical
   inputs reproduce identical unperturbed trajectories. Distinct individuals
   have separate RNG objects and private learned decoders.
2. **Numerical representation:** private sparse overlays produce the same
   synaptic currents as explicit full-weight copies within float32 tolerance
   (`atol=1e-6`, `rtol=1e-5`). Base weights remain read-only.
3. **Continuous time:** after N world ticks, all 24 real brains have N steps.
   Voltages, noise, spikes and steps survive job/window/feedback boundaries.
4. **Replay:** save halfway through an observation, restore, supply identical
   subsequent events, and compare the resulting full state. Include pending
   feedback and matched-control state; a restored rating alone is insufficient.
5. **Stimulus causality:** paired job experiments use seeds 301, 509 and 701 and
   four frozen real jobs. Removing wiring or olfactory input must remove the
   measured downstream job response. Mushroom-body intervention is reported
   without assuming it must remove every downstream response.
6. **Virtual movement:** after calibration on 27 direction/intensity conditions,
   test directions -0.9, -0.6, -0.2, 0.2, 0.6 and 0.9 at unseen intensity 1.1,
   using three held-out seeds. Report every result, not training error alone.
7. **Independent learning:** enqueue one human rating, observe separate stimulus
   and modulator events and private updates in all 24 individuals. Changing one
   individual's factors or fitted decoder must not train another individual.
8. **End-to-end operation:** use the real catalog and full connectome, observe
   all flies move and autonomous recommendations without ratings, then exercise
   optional learning and service restart through the deployed browser/API path.

The small synthetic circuits in unit tests check contracts, not biology or job
quality. Full-model scripts use frozen source-linked real listings and Thomas
Davis's public resume. Experiment artifacts retain parameters and provenance.

## Limits that independent brains do not resolve

- Wiring is anatomical data; synapse signs, normalization, LIF constants, tonic
  drive and noise are modeling assumptions. Fly.ai documents failure of some
  natural visual pathways under its simplified spiking model. The LC10a feature
  channel and virtual-body readout are explicit adapters.
- The local text embedding and ORN projection are artificial. The brain has not
  evolved or been biologically validated to understand job descriptions.
- The dopamine-gated update is an engineered rule, not a measured biological
  dopamine/receptor model. The kernel readout is ordinary supervised computation.
- The flies share anatomy and encoders. Repeated agreement is not 24 independent
  statistical samples from nature. Recruitment and novelty scheduling are code.
- No claim of better job matching is justified without held-out human relevance
  judgments and comparisons against an embedding-only ranker, a learned readout
  without the connectome, shuffled wiring, and frozen/no-plasticity variants.
  Those comparisons need a separate dataset and evaluation; engagement, neural
  activity, landing counts and test coverage are not substitutes for accuracy.

Primary sources: [fly.ai and its stated limitations](https://github.com/alextitonis/fly.ai),
[MaleCNS anatomical data](https://male-cns.janelia.org/).
