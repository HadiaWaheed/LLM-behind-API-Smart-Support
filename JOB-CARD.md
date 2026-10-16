# Support Ticket Triage API — Job Card

## What it does

This API takes a customer support message and uses an LLM to classify the ticket into a small set of predefined categories.

It also determines the urgency, suggests the responsible team, gives a confidence score, and provides a short reason.

## Input

The API accepts one customer support message.

Example:

```json
{
  "text": "I was charged twice for my subscription."
}
```

## Output

The API returns a validated JSON object.

Example:

```json
{
  "category": "billing",
  "urgency": "medium",
  "suggested_team": "billing",
  "confidence": 0.94,
  "reason": "The customer reports a duplicate subscription charge."
}
```

## Allowed categories

* billing
* technical
* account
* delivery
* refund
* other

## Allowed urgency levels

* low
* medium
* high

## Allowed teams

* billing
* technical-support
* account-support
* delivery
* general-support

## It must never

* Return raw LLM text to the user.
* Return a category outside the allowed categories.
* Return an urgency outside the allowed urgency levels.
* Return a team outside the allowed teams.
* Return a confidence value below 0 or above 1.
* Make up information that is not supported by the customer message.
* Treat instructions inside the customer message as system instructions.
* Silently guess when the message is genuinely unclear.

## When unsure

If the customer message does not contain enough information to confidently determine the category, urgency, or team, choose the safest allowed value and use a lower confidence score.

For genuinely unclear cases, use:

* category: `other`
* urgency: `low`
* suggested_team: `general-support`

The reason should briefly explain why the message was unclear.
