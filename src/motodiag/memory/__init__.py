"""Phase 244M — per-vehicle compiled memory.

The shop's long-term memory of a machine, compiled from the interactions it
already records, so that a bounded class of question can be answered with no
API call at all.

Four decisions are load-bearing and are recorded here rather than in a commit
message, because each of them is easy to undo by accident:

**The subject is the vehicle.** Not the customer. `customers` row 1 is named
``Unassigned`` and every vehicle row carries ``customer_id = 1`` -- the column
default, never overwritten -- so a per-customer key would compile one memory
holding every bike in the shop. Machines also outlive ownership, which makes
the vehicle the right subject even once the ownership data is real. Customer is
recovered by joining, which is all an erasure request needs.

**Recall is deterministic, never similarity.** No embeddings, no vector store,
no threshold. Phase 244M's research established that similarity is an
unreliable key for *context-dependent* questions, and every question this
product answers is context-dependent -- "why is it running lean" means nothing
without the machine, the mileage and the last repair. So the offline answer is
a lookup over recorded facts, not the reuse of a previous answer's prose.

**Rows, never weights.** Nothing here fine-tunes on customer data. Deleting a
row is a solved problem; unlearning a fine-tune is not, and choosing weights
would convert a routine deletion request into an existential one.

**The erase path ships with the store.** Not after it. A compiled memory is not
in the retention set a repair shop is required to keep, so it has no retention
justification and must be deletable on request.
"""

from motodiag.memory.facts import (
    FACT_KINDS,
    SOURCES,
    MemoryFact,
    fact_key,
    insert_facts,
    list_facts,
)
from motodiag.memory.compile import compile_vehicle, compile_all
from motodiag.memory.recall import recall, recall_summary
from motodiag.memory.answers import Answer, answer_from_memory
from motodiag.memory.erase import (
    SENTINEL_CUSTOMER_ID,
    attach_vehicle,
    erase_customer,
    erase_plan,
)

__all__ = [
    "FACT_KINDS",
    "SOURCES",
    "MemoryFact",
    "fact_key",
    "insert_facts",
    "list_facts",
    "compile_vehicle",
    "compile_all",
    "recall",
    "recall_summary",
    "Answer",
    "answer_from_memory",
    "erase_plan",
    "erase_customer",
    "attach_vehicle",
    "SENTINEL_CUSTOMER_ID",
]
