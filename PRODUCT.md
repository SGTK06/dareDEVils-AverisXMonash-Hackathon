# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Shipping operations staff triaging a shared inbox and resolving document exceptions.

## Product Purpose

Classify inbound shipping emails, compare Shipping Instructions against draft Bills of Lading, and route uncertain or defective cases to a human for correction.

## Positioning

The workflow combines inbox intent classification, evidence-backed document comparison, confidence-aware escalation, and a correction loop in one operations workspace.

## Operating Context

The system processes synthetic or connected inbox records with SI/BL attachments. Operators inspect evidence, edit extracted values when needed, and export the resulting submission.

## Capabilities and Constraints

- Categories: BL comparison, SI request, invoice query, general, and spam.
- Comparison fields: shipper, consignee, notify party, ports, container count, and gross weight.
- Low confidence, missing values, wrong document types, and unreadable documents must become `NEEDS_REVIEW`, never a guessed mismatch.
- Classifications and review corrections are persisted to Supabase when configured.

## Product Principles

- Escalate uncertainty instead of guessing.
- Keep source evidence beside every decision.
- Make operator corrections explicit, editable, and auditable.
- Keep tuning parameters in configuration, not scattered through request handlers.

## Accessibility & Inclusion

Keyboard-accessible controls, visible focus states, readable contrast, and responsive layouts are required for the operations workspace.
