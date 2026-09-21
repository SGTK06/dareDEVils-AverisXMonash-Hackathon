A shipping operations team receives different kinds of messages in the same inbox: requests to check
documents, prepare new shipping instructions, answer invoice questions, and share operational
updates. Spam arrives alongside them.
For a document-checking request, the team compares a Shipping Instruction (SI), which contains the
intended shipment details, with a draft Bill of Lading (BL). The SI is the reference for this check. The
goal is to catch incorrect details before the draft is finalized.
The problems
Finding the right emails takes time. Staff must read each message and decide what action it
needs. A document request that is overlooked never reaches the checking step.
Manual comparison is repetitive and easy to get wrong. Names, ports, quantities, and weight
must be checked across two documents. A missed discrepancy can lead to corrections, delays, and
additional work.
The same information can look different. One document may say “Port of Loading” while the
other says “Load Port.” The system needs to recognize that these refer to the same field.
What the system should be able to do
Starting from the inbox, the system should produce a clear result for each email. How you design the
workflow is up to you, but it should generally be able to:
Capability What it means

Classify Tell the different kinds of messages apart, including document-
comparison requests, new SI requests, invoice queries, general

messages, and spam.
