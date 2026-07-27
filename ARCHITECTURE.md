# Hybrid Architecture Sketch

1. **Buzz Layer** (Nostr relay + channels)
   - Humans + agents as first-class members
   - Signed events for everything

2. **Runtime Core** (ZeroClaw DNA)
   - Single binary or WASM modules
   - Capability-based permissions
   - Encrypted secrets, filesystem scoping

3. **Proactive Brain** (OpenAGI DNA)
   - Background observer (screen/activity opt-in)
   - Signal scoring before action
   - Skill auto-generation + specialist agents

4. **Glue**
   - Agent Client Protocol (ACP) adapters
   - Shared memory via Buzz events + local GRAPH/RAG

Result: agents that don't wait to be asked, can't be easily poisoned, and collaborate natively in the same room as humans.
