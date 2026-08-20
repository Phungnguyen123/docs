# Chatbot & CS Team Handoff on Chatwoot — Video Narration Script
Source deck: Chatwoot Handoff Guide (Option D, v.190826) · Audience: CS Team · Target runtime: 8–10 minutes

---

## 0. Framing for NotebookLM
- **Goal of the video:** a new CS agent can run the handoff correctly on WhatsApp and on the BSmart Livechat after one watch.
- **Tone:** practical, calm, instructional. No marketing language.
- **Recurring line to repeat at least three times:** "Assignee decides WHO answers. Status decides WHEN the bot answers."
- **Hard rule to end on:** on Chatwoot v4.16.2, assigning an agent is not enough — the status must be moved off Pending.

---

## Section 1 — Opening (Slide 1)
Welcome. This guide covers how the CS team hands a conversation over to BSmart, our AI assistant, and how BSmart hands it back. It applies to two channels: WhatsApp and the Livechat widget on our website. Everything is done inside Chatwoot, using only two fields on the conversation.

## Section 2 — The two rules (Slides 2–3)
There are only two fields to think about.

The first is **Assignee**, and it answers the question *who*. If a CS agent is assigned, the bot is off. If the Agent Bot is assigned, or the conversation is unassigned, the bot is ready to run.

The second is **Status**, and it answers the question *when*. **Pending** means the bot works to our business hours: it replies during the working window, and outside it tells the customer when the team is back. **Open** means the bot serves immediately and around the clock, ignoring business hours.

Put together, four combinations cover every conversation we handle:
1. Agent Bot with Pending — the bot greets new arrivals during business hours.
2. A CS name with Open — the bot is fully off and the agent owns every reply.
3. Agent Bot with Open — the bot takes over a live case immediately, 24/7.
4. Any assignee with Resolved — the ticket is closed and the bot skips it.

## Section 3 — WhatsApp, step by step (Slides 4–9)
**Step 1, first contact.** A customer sends their first WhatsApp message. Chatwoot sets the assignee to Unassigned or Agent Bot, and the status to Pending. The bot answers from its script during business hours. No CS action is needed.

**Step 2, CS takes over.** When the case needs a person, assign the conversation to yourself and set the status to Open. The bot stops replying entirely, and every message from that point is yours.

**Step 3, hand back to the bot.** If you get busy or your shift ends mid-conversation, change one field only: the assignee, back to Agent Bot. Leave the status on Open. Because it stays Open, the bot replies immediately and keeps covering the case overnight.

**Step 4, close the case.** Once the request is settled, set the status to Resolved. The assignee no longer matters. The conversation is complete and the bot skips it.

**After Resolved.** If the customer messages again later, Chatwoot opens a new conversation with the Agent Bot assigned and the status Pending. The original flow restarts, and the four steps repeat.

## Section 4 — Livechat overview (Slides 10–11)
The same two rules apply on the BSmart Livechat widget on our website. There is one extra path: the customer can ask for a human themselves, using the "Talk to Agent" button.

Five scenarios cover the channel: a new visitor arrives; CS takes over; the bot covers the shift; the customer asks for a human; and the case is closed and later re-opened.

## Section 5 — Livechat, step by step (Slides 12–25)
**Scenario 1, new visitor arrives.** An anonymous visitor sends the first message. BSmart greets them and handles the conversation. Assignee: Agent Bot. Status: Pending. Nothing for CS to do. Outside working hours, the bot tells the visitor when the team is back.

**Scenario 2, CS takes over.** Assign the conversation to yourself and set the status to Open. The bot skips it automatically, and the widget tells the customer they are now connected to a person.

**Scenario 3, the bot covers the shift.** You are mid-conversation, but you are pulled away or your shift ends. Change the assignee back to Agent Bot and leave the status as it is. Keeping it on Open is what gives round-the-clock cover; switching it to Pending would put the bot back on business hours.

**Scenario 4, the customer asks for a human.** The customer clicks "Talk to Agent" and submits the contact form. Two things happen: the contact changes from anonymous to identified in Chatwoot, so you now have a name and an email, and the bot posts the working-hours note while flagging the request for CS. Watch for these in the inbox — these are customers who explicitly asked for a person. If the customer instead chooses "Continue with BSmart", the bot keeps the conversation and no action is needed.

**Scenario 5, close and re-open.** Set the status to Resolved when the case is handled. If the customer writes again, the ticket re-opens as Pending and routes from the start, with the earlier context history attached. Nothing is lost.

## Section 6 — Closing and the version warning (Slide 26)
Three habits to take away.

First, assign before you reply. Put your name on the conversation and set it to Open, or the bot will keep answering alongside you.

Second, hand back rather than park. Leaving a case Open and assigned to you at the end of your shift leaves the customer waiting. Reassign it to the Agent Bot.

Third, resolve when you are finished. Resolved keeps the queue clean, and the customer's next message reopens the flow at Pending automatically.

And one important note for Chatwoot version 4.16.2. Assigning an agent is not enough. You must change the status away from Pending, to Open. In newer versions, assigning an agent no longer opens the chat automatically, so changing the status manually is what prevents the bot from replying over the top of you.

---

## Suggested chapter markers
| Time | Chapter |
| --- | --- |
| 0:00 | Why this guide |
| 0:40 | Assignee = WHO, Status = WHEN |
| 1:40 | The four combinations |
| 2:30 | WhatsApp: four steps |
| 4:30 | Livechat: five scenarios |
| 7:30 | Talk to Agent form |
| 8:30 | Habits + v4.16.2 warning |

## Knowledge-check questions (optional end card)
1. A customer is waiting and you are about to reply. Which two fields do you set, and to what?
2. Your shift ends mid-chat. What do you change, and what do you deliberately leave alone?
3. You assigned the Agent Bot but left the status on Pending, outside working hours. What does the customer experience?
4. What happens when a resolved customer messages again?
