"""The synthetic mailbox: 40 messages covering every category, priority and screen.

Sized to ``api.DEFAULT_LIMIT`` (40) on purpose — anything beyond that is invisible in
the inbox, and an action pointing at a message you cannot open looks broken on camera.

Design notes
------------
* **Fictional senders only.** No real company appears here. A public screen recording
  that shows "HDFC Bank" sending a fabricated email puts words in a real organisation's
  mouth; invented names record exactly as well and carry no such risk.
* **Content images use a real host** (``picsum.photos``) so the "Load images" button has
  something visible to load on camera. **Tracking pixels use ``.example``**, a reserved
  TLD that can never resolve — they exist to be counted and blocked, not fetched.
* **Ages are relative** (``h`` = hours before seed time), so the inbox looks fresh
  whenever it is rebuilt rather than drifting into obviously stale dates.
* Several ``body_text`` fields are deliberately ugly — long tracking URLs, collapsed
  whitespace — because that is what real ``text/plain`` fallbacks look like, and it is
  what makes the summary-first reader worth demonstrating.

A few threads are planted so the Ask screen has real answers: a flight (SW-4021), a
stay with a wifi password, a set of receipts that sum to a checkable number, and a
domain that expires soon.
"""

from __future__ import annotations

PERSONA_NAME = "Arjun Mehta"
PERSONA_EMAIL = "arjun.mehta@zephyrmail.com"

_PIXEL = '<img src="https://track.mailmetrics.example/o.gif?c={cid}" width="1" height="1" alt="">'


def _shell(inner: str, *, brand: str, accent: str = "#1f6feb", cid: str = "x") -> str:
    """A marketing-style HTML email: table layout, inline CSS, a tracking pixel."""
    return f"""<html><body style="margin:0;padding:0;background:#f4f5f7;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f5f7;padding:24px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;font-family:-apple-system,Segoe UI,Roboto,sans-serif;">
<tr><td style="background:{accent};padding:20px 28px;color:#fff;font-size:19px;font-weight:600;">{brand}</td></tr>
<tr><td style="padding:28px;color:#1b1f24;font-size:15px;line-height:1.65;">{inner}</td></tr>
<tr><td style="padding:18px 28px;background:#fafbfc;color:#6a737d;font-size:11px;line-height:1.5;">
You are receiving this because you have an account with {brand}.
<a href="https://{brand.lower().replace(' ', '')}.example/unsub" style="color:#6a737d;">Unsubscribe</a> &middot;
<a href="https://{brand.lower().replace(' ', '')}.example/prefs" style="color:#6a737d;">Email preferences</a>
</td></tr>
</table></td></tr></table>
{_PIXEL.format(cid=cid)}
</body></html>"""


# Each entry: h = hours ago. `html` is optional — plain-text-only mail is realistic too.
MESSAGES: list[dict] = [
    # ---------------------------------------------------------------- Travel
    {
        "h": 30, "cat": "Travel", "prio": "action", "unread": 1,
        "name": "Skyward Airlines", "addr": "bookings@skywardair.example",
        "subj": "Your booking SW-4021 is confirmed",
        "tldr": "Bengaluru to Singapore on Sat 14 Sept, departing 06:20. PNR QJ7RM2, seat 14A. Web check-in opens 48 hours before.",
        "snippet": "Booking confirmed. BLR to SIN, 14 September 2026, 06:20.",
        "body": "Your booking is confirmed.\r\n\r\nPNR: QJ7RM2\r\nFlight SW-4021  Bengaluru (BLR) -> Singapore (SIN)\r\nDate: Saturday, 14 September 2026\r\nDeparture: 06:20  Arrival: 13:45\r\nSeat: 14A   Baggage: 25kg checked, 7kg cabin\r\n\r\nManage booking: https://skywardair.example/mb?t=8f2a1c4b9e&u=arjun\r\nWeb check-in opens 48 hours before departure.",
        "html": _shell(
            "<h2 style='margin:0 0 6px;font-size:21px;'>Your trip is confirmed</h2>"
            "<p style='margin:0 0 18px;color:#57606a;'>PNR <strong>QJ7RM2</strong></p>"
            "<table width='100%' style='border-collapse:collapse;font-size:14px;'>"
            "<tr><td style='padding:9px 0;border-bottom:1px solid #eaeef2;color:#57606a;'>Flight</td><td style='padding:9px 0;border-bottom:1px solid #eaeef2;text-align:right;'><strong>SW-4021</strong></td></tr>"
            "<tr><td style='padding:9px 0;border-bottom:1px solid #eaeef2;color:#57606a;'>Route</td><td style='padding:9px 0;border-bottom:1px solid #eaeef2;text-align:right;'>Bengaluru (BLR) &rarr; Singapore (SIN)</td></tr>"
            "<tr><td style='padding:9px 0;border-bottom:1px solid #eaeef2;color:#57606a;'>Date</td><td style='padding:9px 0;border-bottom:1px solid #eaeef2;text-align:right;'>Saturday, 14 September 2026</td></tr>"
            "<tr><td style='padding:9px 0;border-bottom:1px solid #eaeef2;color:#57606a;'>Departs</td><td style='padding:9px 0;border-bottom:1px solid #eaeef2;text-align:right;'><strong>06:20</strong></td></tr>"
            "<tr><td style='padding:9px 0;border-bottom:1px solid #eaeef2;color:#57606a;'>Arrives</td><td style='padding:9px 0;border-bottom:1px solid #eaeef2;text-align:right;'>13:45</td></tr>"
            "<tr><td style='padding:9px 0;color:#57606a;'>Seat</td><td style='padding:9px 0;text-align:right;'>14A</td></tr></table>"
            "<p style='margin:22px 0 0;'><a href='https://skywardair.example/mb' style='background:#1f6feb;color:#fff;padding:11px 20px;border-radius:8px;text-decoration:none;font-weight:600;'>Manage booking</a></p>",
            brand="Skyward Airlines", cid="sw4021"),
    },
    {
        "h": 26, "cat": "Travel", "prio": "action", "unread": 1,
        "name": "Northwood Stays", "addr": "host@northwoodstays.example",
        "subj": "Check-in details for the Marina Bay loft",
        "tldr": "Self check-in from 15:00 on 14 Sept. Door code 4417. Wifi network NorthwoodGuest, password marina-bay-2026. Checkout 11:00 on the 19th.",
        "snippet": "Self check-in from 3pm. Door code and wifi inside.",
        "body": "Hi Arjun,\r\n\r\nLooking forward to hosting you. Everything you need:\r\n\r\nAddress: 42 Marina View, Level 9, Singapore\r\nCheck-in: from 15:00 on 14 September (self check-in)\r\nDoor code: 4417\r\nWifi network: NorthwoodGuest\r\nWifi password: marina-bay-2026\r\nCheckout: 11:00 on 19 September\r\n\r\nThe building entrance is on the east side. Message me if anything is unclear.\r\n\r\n- Wei",
    },
    {
        "h": 74, "cat": "Travel", "prio": "fyi", "unread": 0,
        "name": "Trailhead Travel", "addr": "trips@trailheadtravel.example",
        "subj": "Your Singapore itinerary is ready",
        "tldr": "Five-day itinerary with the Gardens by the Bay booking on day two and a free day on the 17th.",
        "snippet": "Day-by-day plan attached, including your Gardens booking.",
        "body": "Your itinerary for 14-19 September is ready. Day 2 includes the Gardens by the Bay entry you pre-booked (10:30). Day 4 is unscheduled.\r\n\r\nView: https://trailheadtravel.example/i/9f3k2",
    },
    {
        "h": 120, "cat": "Travel", "prio": "ignore", "unread": 0,
        "name": "Skyward Airlines", "addr": "offers@skywardair.example",
        "subj": "Monsoon fares from ₹2,199 — book by Sunday",
        "tldr": "Promotional fare sale across 40 domestic routes, ending Sunday.",
        "snippet": "Fares from ₹2,199 on 40 routes. Ends Sunday.",
        "body": "MONSOON SALE  Fares from Rs 2199  Book by Sunday  https://skywardair.example/c?u=aHR0cHM6Ly9za3l3YXJkYWlyL3NhbGU&t=8812f4a9c1e77b2d0a&s=email&m=promo  Terms apply  Unsubscribe https://skywardair.example/u?id=99f2a1",
        "html": _shell(
            "<img src='https://picsum.photos/seed/skyward/544/200' width='544' style='border-radius:8px;display:block;margin-bottom:18px;' alt='Monsoon sale'>"
            "<h2 style='margin:0 0 8px;'>Monsoon fares from ₹2,199</h2>"
            "<p style='margin:0 0 16px;color:#57606a;'>Across 40 domestic routes. Book by Sunday.</p>"
            "<p><a href='https://skywardair.example/sale' style='background:#1f6feb;color:#fff;padding:11px 20px;border-radius:8px;text-decoration:none;'>See fares</a></p>",
            brand="Skyward Airlines", cid="promo01"),
    },

    # ------------------------------------------------------------------ Work
    {
        "h": 5, "cat": "Work", "prio": "action", "unread": 1,
        "name": "Priya Raghavan", "addr": "priya.raghavan@nordlight.example",
        "subj": "Q3 roadmap review — Thursday 3pm",
        "tldr": "Priya needs your three roadmap slides by Wednesday end of day, ahead of Thursday's 3pm review with the leadership team.",
        "snippet": "Can you get me your three slides by Wednesday EOD?",
        "body": "Hi Arjun,\r\n\r\nThe Q3 roadmap review is confirmed for Thursday at 3pm with the leadership team.\r\n\r\nCould you send me your three slides by Wednesday end of day so I can merge the deck? Specifically:\r\n  1. What shipped in Q2\r\n  2. The two bets for Q3\r\n  3. What you are explicitly not doing\r\n\r\nKeep it short - they will ask questions.\r\n\r\nThanks,\r\nPriya",
    },
    {
        "h": 9, "cat": "Work", "prio": "action", "unread": 1,
        "name": "Dev Kulkarni", "addr": "dev.kulkarni@nordlight.example",
        "subj": "PR #482 needs your review before the freeze",
        "tldr": "Dev is blocked on your review of PR #482 (auth token refresh). Code freeze is Friday.",
        "snippet": "Blocked on your review — freeze is Friday.",
        "body": "Hey, PR #482 (auth token refresh) has been open since Monday. I'm blocked on your review and the freeze is Friday.\r\n\r\nIt's about 200 lines, mostly the retry path. https://git.nordlight.example/core/pull/482",
    },
    {
        "h": 22, "cat": "Work", "prio": "fyi", "unread": 0,
        "name": "Meera Shah", "addr": "meera.shah@nordlight.example",
        "subj": "Design handoff — settings screen",
        "tldr": "Settings screen designs are final and in Figma. Meera flagged that the privacy toggle copy still needs a legal read.",
        "snippet": "Designs are final. Privacy toggle copy still needs legal.",
        "body": "Handoff is done - settings screen is final in Figma. One open item: the privacy toggle copy hasn't had a legal read yet, so treat that string as provisional.",
    },
    {
        "h": 47, "cat": "Work", "prio": "fyi", "unread": 0,
        "name": "Atlas Analytics", "addr": "reports@atlasanalytics.example",
        "subj": "Your weekly team report",
        "tldr": "Deploys up 18% week on week, median review time down to 6.2 hours, one incident (resolved in 41 minutes).",
        "snippet": "Deploys +18%, review time 6.2h, one resolved incident.",
        "body": "Week of 22 Aug\r\n  Deploys: 34 (+18%)\r\n  Median review time: 6.2h (-1.4h)\r\n  Incidents: 1, resolved in 41m\r\n\r\nFull report: https://atlasanalytics.example/r/week34",
    },
    {
        "h": 53, "cat": "Work", "prio": "fyi", "unread": 0,
        "name": "Nikhil Rao", "addr": "nikhil.rao@nordlight.example",
        "subj": "Re: sprint planning notes",
        "tldr": "Nikhil moved the search reindex work to next sprint; no action needed from you.",
        "snippet": "Moved the reindex to next sprint. No action for you.",
        "body": "Following up on planning - I've moved the search reindex to next sprint since the infra work isn't ready. Nothing needed from you, just flagging.",
    },
    {
        "h": 96, "cat": "Work", "prio": "ignore", "unread": 0,
        "name": "Nordlight Helpdesk", "addr": "no-reply@helpdesk.nordlight.example",
        "subj": "Ticket #9931 has been resolved",
        "tldr": "Your VPN access ticket was resolved and closed automatically.",
        "snippet": "Ticket #9931 resolved and closed.",
        "body": "Ticket #9931 (VPN access) has been marked resolved and will close automatically in 72 hours. Do not reply to this message.",
    },

    # --------------------------------------------------------------- Finance
    {
        "h": 3, "cat": "Urgent", "prio": "action", "unread": 1,
        "name": "Meridian Bank", "addr": "alerts@meridianbank.example",
        "subj": "Sign-in attempt blocked — was this you?",
        "tldr": "A sign-in from a new device in Pune was blocked at 02:14. Confirm it was you or lock the account within 24 hours.",
        "snippet": "New device blocked at 02:14. Confirm or lock the account.",
        "body": "We blocked a sign-in to your account.\r\n\r\nTime: 02:14 IST\r\nDevice: Android (new)\r\nLocation: Pune, IN\r\n\r\nIf this was you, confirm in the app. If not, lock your account immediately. We will never ask for your PIN or OTP by email.",
        "html": _shell(
            "<h2 style='margin:0 0 10px;'>We blocked a sign-in</h2>"
            "<table width='100%' style='border-collapse:collapse;font-size:14px;'>"
            "<tr><td style='padding:8px 0;color:#57606a;'>Time</td><td style='padding:8px 0;text-align:right;'>02:14 IST</td></tr>"
            "<tr><td style='padding:8px 0;color:#57606a;'>Device</td><td style='padding:8px 0;text-align:right;'>Android (new)</td></tr>"
            "<tr><td style='padding:8px 0;color:#57606a;'>Location</td><td style='padding:8px 0;text-align:right;'>Pune, IN</td></tr></table>"
            "<p style='margin:20px 0 0;'><a href='https://meridianbank.example/lock' style='background:#cf222e;color:#fff;padding:11px 20px;border-radius:8px;text-decoration:none;font-weight:600;'>This wasn't me</a></p>"
            "<p style='margin:18px 0 0;font-size:13px;color:#57606a;'>We will never ask for your PIN or OTP by email.</p>",
            brand="Meridian Bank", accent="#cf222e", cid="sec01"),
    },
    {
        "h": 18, "cat": "Finance", "prio": "action", "unread": 1,
        "name": "Cobalt Card", "addr": "statements@cobaltcard.example",
        "subj": "Payment of ₹12,430 due on 5 September",
        "tldr": "Cobalt Card bill of ₹12,430 is due 5 September. Minimum due ₹620; autopay is not set up on this card.",
        "snippet": "₹12,430 due 5 Sept. Autopay is not enabled.",
        "body": "Statement summary\r\n  Total due: Rs 12,430.00\r\n  Minimum due: Rs 620.00\r\n  Due date: 5 September 2026\r\n\r\nAutopay is not enabled on this card. Pay: https://cobaltcard.example/pay?r=7c2f",
    },
    {
        "h": 64, "cat": "Finance", "prio": "fyi", "unread": 0,
        "name": "Meridian Bank", "addr": "statements@meridianbank.example",
        "subj": "Your August 2026 statement is ready",
        "tldr": "August statement available. Closing balance ₹1,84,220 across savings and deposits.",
        "snippet": "August statement ready. Closing balance ₹1,84,220.",
        "body": "Your statement for August 2026 is ready to view. Closing balance across savings and deposits: Rs 1,84,220.\r\n\r\nView securely: https://meridianbank.example/stmt",
    },
    {
        "h": 140, "cat": "Finance", "prio": "fyi", "unread": 0,
        "name": "Ledgerly", "addr": "reminders@ledgerly.example",
        "subj": "Advance tax instalment due 15 September",
        "tldr": "Second advance tax instalment is due 15 September. Ledgerly estimates ₹31,000 based on your filed figures.",
        "snippet": "Second instalment due 15 Sept, estimated ₹31,000.",
        "body": "The second advance tax instalment is due 15 September. Based on the figures you filed last quarter we estimate Rs 31,000. Review before paying.",
    },

    # -------------------------------------------------------------- Receipts
    {
        "h": 8, "cat": "Receipts", "prio": "ignore", "unread": 0,
        "name": "Lumen Coffee", "addr": "receipts@lumencoffee.example",
        "subj": "Receipt — ₹480",
        "tldr": "Card payment of ₹480 at Lumen Coffee, Indiranagar.",
        "snippet": "₹480 paid at Lumen Coffee, Indiranagar.",
        "body": "Thanks for visiting.\r\n\r\n2x Filter coffee   Rs 260\r\n1x Almond croissant  Rs 220\r\nTotal: Rs 480.00\r\nCard ending 4417",
    },
    {
        "h": 34, "cat": "Receipts", "prio": "ignore", "unread": 0,
        "name": "Verdant Grocers", "addr": "orders@verdantgrocers.example",
        "subj": "Order #88213 delivered — ₹2,340",
        "tldr": "Grocery order of ₹2,340 delivered on Tuesday.",
        "snippet": "Order #88213 delivered. Total ₹2,340.",
        "body": "Your order #88213 was delivered.\r\n\r\n18 items  Total: Rs 2,340.00\r\nPaid by UPI",
    },
    {
        "h": 58, "cat": "Receipts", "prio": "fyi", "unread": 0,
        "name": "Orbit Electronics", "addr": "invoice@orbitelectronics.example",
        "subj": "Invoice #INV-77401 — ₹18,999",
        "tldr": "Invoice for noise-cancelling headphones, ₹18,999. Two-year warranty registered, returns open until 20 September.",
        "snippet": "Headphones, ₹18,999. Returns open until 20 Sept.",
        "body": "Invoice INV-77401\r\n\r\nAurex NC-700 noise-cancelling headphones   Rs 18,999.00\r\nWarranty: 2 years (registered)\r\nReturn window closes 20 September 2026",
        "html": _shell(
            "<h2 style='margin:0 0 6px;'>Invoice INV-77401</h2>"
            "<img src='https://picsum.photos/seed/orbit/200/140' width='200' style='border-radius:8px;float:right;margin:0 0 12px 16px;' alt='Headphones'>"
            "<p style='margin:0 0 14px;color:#57606a;'>Aurex NC-700 noise-cancelling headphones</p>"
            "<table style='border-collapse:collapse;font-size:14px;'>"
            "<tr><td style='padding:7px 24px 7px 0;color:#57606a;'>Amount</td><td style='padding:7px 0;'><strong>₹18,999.00</strong></td></tr>"
            "<tr><td style='padding:7px 24px 7px 0;color:#57606a;'>Warranty</td><td style='padding:7px 0;'>2 years, registered</td></tr>"
            "<tr><td style='padding:7px 24px 7px 0;color:#57606a;'>Returns close</td><td style='padding:7px 0;'>20 September 2026</td></tr></table>",
            brand="Orbit Electronics", accent="#8250df", cid="inv774"),
    },
    {
        "h": 30, "cat": "Receipts", "prio": "fyi", "unread": 0,
        "name": "Skyward Airlines", "addr": "receipts@skywardair.example",
        "subj": "Fare receipt for SW-4021 — ₹24,150",
        "tldr": "Fare receipt for the Singapore flight, ₹24,150 including taxes.",
        "snippet": "₹24,150 paid for booking QJ7RM2.",
        "body": "Fare receipt\r\n\r\nPNR QJ7RM2  SW-4021 BLR-SIN\r\nBase fare  Rs 19,400\r\nTaxes and fees  Rs 4,750\r\nTotal  Rs 24,150.00",
    },
    {
        "h": 72, "cat": "Receipts", "prio": "ignore", "unread": 0,
        "name": "Northwood Stays", "addr": "billing@northwoodstays.example",
        "subj": "Payment received — ₹9,800",
        "tldr": "Accommodation payment of ₹9,800 for five nights at the Marina Bay loft.",
        "snippet": "₹9,800 received for 5 nights.",
        "body": "Payment received: Rs 9,800.00 for 5 nights (14-19 September), Marina Bay loft.",
    },

    # ---------------------------------------------------------------- Urgent
    {
        "h": 11, "cat": "Urgent", "prio": "action", "unread": 1,
        "name": "Vertex Domains", "addr": "renewals@vertexdomains.example",
        "subj": "zephyr-notes.dev expires in 6 days",
        "tldr": "Domain zephyr-notes.dev expires on 4 September. Auto-renew is off; the site goes down if it lapses.",
        "snippet": "Expires 4 Sept. Auto-renew is off.",
        "body": "Your domain zephyr-notes.dev expires on 4 September 2026.\r\n\r\nAuto-renew is currently OFF. If the domain lapses, DNS stops resolving and the site will go down. Renewal: Rs 1,180 for one year.\r\n\r\nRenew: https://vertexdomains.example/renew?d=zephyr-notes.dev",
    },

    # -------------------------------------------------------------- Personal
    {
        "h": 6, "cat": "Personal", "prio": "action", "unread": 1,
        "name": "Amma", "addr": "lakshmi.mehta@zephyrmail.com",
        "subj": "Call me when you land",
        "tldr": "Your mother wants a call once you land in Singapore, and asks whether you need the blue suitcase.",
        "snippet": "Call once you land. Do you want the blue suitcase?",
        "body": "Beta,\r\n\r\nCall me once you land, not before - I know it will be late here.\r\n\r\nAlso do you want the blue suitcase? It is bigger. Let me know before Thursday so I can bring it over.\r\n\r\n- Amma",
    },
    {
        "h": 40, "cat": "Personal", "prio": "action", "unread": 0,
        "name": "Bridgeway Dental", "addr": "front-desk@bridgewaydental.example",
        "subj": "Appointment reminder — 3 September, 11:00",
        "tldr": "Dental cleaning on 3 September at 11:00. Confirm 24 hours ahead or the slot is released.",
        "snippet": "Cleaning on 3 Sept, 11:00. Confirm 24h ahead.",
        "body": "Reminder: cleaning appointment on 3 September at 11:00 with Dr Nair.\r\n\r\nPlease confirm at least 24 hours in advance or the slot will be released to the waiting list.",
    },
    {
        "h": 88, "cat": "Personal", "prio": "fyi", "unread": 0,
        "name": "Rohan Iyer", "addr": "rohan.iyer@zephyrmail.com",
        "subj": "Trek plan for October?",
        "tldr": "Rohan is proposing a Kudremukh trek in mid-October and wants to know if you're in before he books.",
        "snippet": "Kudremukh in mid-October — are you in?",
        "body": "Thinking Kudremukh, second weekend of October. Three of us so far. Permits need booking three weeks out so let me know in the next week or so - no rush this second.",
    },

    # ----------------------------------------------------------- Newsletters
    {
        "h": 14, "cat": "Newsletters", "prio": "fyi", "unread": 0,
        "name": "The Quiet Standard", "addr": "hello@quietstandard.example",
        "subj": "Issue 112 — The cost of a default",
        "tldr": "Essay on how software defaults shape behaviour more than settings do.",
        "snippet": "This week: why defaults outweigh settings.",
        "body": "THE QUIET STANDARD  Issue 112\r\n\r\nThe cost of a default\r\n\r\nMost people never open the settings screen. Which means the default is not a starting point - it is the product...\r\n\r\nRead online: https://quietstandard.example/112?utm_source=newsletter&utm_medium=email&utm_campaign=issue112&sub=a91f2c",
        "html": _shell(
            "<h2 style='margin:0 0 6px;font-size:20px;'>The cost of a default</h2>"
            "<p style='margin:0 0 16px;color:#8b949e;font-size:13px;'>Issue 112 &middot; 6 min read</p>"
            "<img src='https://picsum.photos/seed/quiet/544/220' width='544' style='border-radius:8px;display:block;margin-bottom:18px;' alt=''>"
            "<p>Most people never open the settings screen. Which means the default is not a starting point — it is the product.</p>"
            "<p>We spend enormous effort on the options and almost none on the state everyone actually lives in…</p>"
            "<p style='margin-top:20px;'><a href='https://quietstandard.example/112' style='color:#1f6feb;'>Continue reading &rarr;</a></p>",
            brand="The Quiet Standard", accent="#24292f", cid="qs112"),
    },
    {"h": 38, "cat": "Newsletters", "prio": "ignore", "unread": 0,
     "name": "Frontend Digest", "addr": "weekly@frontenddigest.example",
     "subj": "This week in frontend — view transitions everywhere",
     "tldr": "Weekly roundup covering the View Transitions API landing across browsers.",
     "snippet": "View Transitions ships broadly; plus 9 links.",
     "body": "THIS WEEK  View Transitions API now broadly available  Container queries in practice  9 more links  https://frontenddigest.example/w?id=44f1&u=8812"},
    {"h": 62, "cat": "Newsletters", "prio": "ignore", "unread": 0,
     "name": "Systems Weekly", "addr": "editor@systemsweekly.example",
     "subj": "Issue 89 — Write-ahead logs, explained slowly",
     "tldr": "Long-form explainer on write-ahead logging in embedded databases.",
     "snippet": "WAL explained from first principles.",
     "body": "Issue 89: Write-ahead logs, explained slowly. Starting from why fsync is expensive... https://systemsweekly.example/89?src=em"},
    {"h": 91, "cat": "Newsletters", "prio": "ignore", "unread": 0,
     "name": "Product Teardown", "addr": "team@productteardown.example",
     "subj": "How Linear does onboarding",
     "tldr": "Teardown of an onboarding flow, screenshot by screenshot.",
     "snippet": "Onboarding teardown, 22 screenshots.",
     "body": "This week we walk through an onboarding flow screen by screen. 22 screenshots. https://productteardown.example/t/onboarding?e=a1"},
    {"h": 115, "cat": "Newsletters", "prio": "ignore", "unread": 0,
     "name": "The Cartographer", "addr": "post@cartographer.example",
     "subj": "Maps that lie on purpose",
     "tldr": "Essay on deliberate distortion in transit map design.",
     "snippet": "Why transit maps distort distance deliberately.",
     "body": "Maps that lie on purpose - on why the transit map in your city is geographically wrong, and right to be. https://cartographer.example/lie"},
    {"h": 133, "cat": "Newsletters", "prio": "ignore", "unread": 0,
     "name": "Deep Work Letter", "addr": "letter@deepwork.example",
     "subj": "The two-hour rule",
     "tldr": "Argues for protecting a single two-hour uninterrupted block daily.",
     "snippet": "Protect one two-hour block a day.",
     "body": "The two-hour rule: protect one uninterrupted block per day and let the rest of the calendar fall where it may. https://deepwork.example/2h?u=f4"},

    # ---------------------------------------------------------------- Social
    {"h": 16, "cat": "Social", "prio": "ignore", "unread": 1,
     "name": "LinkNet", "addr": "invitations@linknet.example",
     "subj": "You have 4 new invitations",
     "tldr": "Four pending connection requests on LinkNet.",
     "snippet": "4 people want to connect.",
     "body": "You have 4 new invitations waiting. View them: https://linknet.example/inv?u=88f2a&tk=9911cc"},
    {"h": 44, "cat": "Social", "prio": "ignore", "unread": 0,
     "name": "LinkNet", "addr": "notifications@linknet.example",
     "subj": "Priya and 11 others viewed your profile",
     "tldr": "Twelve profile views this week.",
     "snippet": "12 people viewed your profile this week.",
     "body": "Your profile was viewed 12 times this week. See who: https://linknet.example/views?u=88f2a"},
    {"h": 67, "cat": "Social", "prio": "ignore", "unread": 0,
     "name": "Pixelgram", "addr": "no-reply@pixelgram.example",
     "subj": "3 people tagged you in photos",
     "tldr": "Three new photo tags from the weekend.",
     "snippet": "You were tagged in 3 photos.",
     "body": "3 new tags. Open the app to see them. https://pixelgram.example/n?t=aa71"},
    {"h": 103, "cat": "Social", "prio": "ignore", "unread": 0,
     "name": "DevForum", "addr": "digest@devforum.example",
     "subj": "New replies to your question about SQLite WAL",
     "tldr": "Two new replies on your SQLite question, one marked helpful.",
     "snippet": "2 replies, one marked helpful.",
     "body": "Your question 'SQLite WAL mode with multiple readers' has 2 new replies. https://devforum.example/q/44192"},

    # ------------------------------------------------------ Promotions/noise
    {
        "h": 20, "cat": "Newsletters", "prio": "ignore", "unread": 1,
        "name": "Westgate Retail", "addr": "offers@westgateretail.example",
        "subj": "Monsoon sale — up to 40% off everything",
        "tldr": "Site-wide sale up to 40% off, ending Sunday midnight.",
        "snippet": "Up to 40% off. Ends Sunday midnight.",
        # Deliberately awful text/plain fallback: this is what makes the HTML reader matter.
        "body": "MONSOON SALE  UP TO 40% OFF  SHOP NOW https://westgateretail.example/c?u=aHR0cHM6Ly93ZXN0Z2F0ZXJldGFpbC5leGFtcGxlL3NhbGU&t=99a1f4c2e8&s=email&m=monsoon&p=hero  WOMEN https://westgateretail.example/c?u=d29tZW4&t=99a1f4c2e8  MEN https://westgateretail.example/c?u=bWVu&t=99a1f4c2e8  HOME https://westgateretail.example/c?u=aG9tZQ&t=99a1f4c2e8  ENDS SUNDAY MIDNIGHT  Terms apply. https://westgateretail.example/terms?t=99a1f4c2e8  You are receiving this because you shopped with us. Unsubscribe https://westgateretail.example/u?id=4471f2a9c&h=88b1  View in browser https://westgateretail.example/vib?id=4471f2a9c",
        "html": _shell(
            "<img src='https://picsum.photos/seed/westgate1/544/240' width='544' style='border-radius:8px;display:block;margin-bottom:16px;' alt='Monsoon sale'>"
            "<h2 style='margin:0 0 8px;font-size:24px;'>Up to 40% off everything</h2>"
            "<p style='margin:0 0 18px;color:#57606a;'>Ends Sunday at midnight.</p>"
            "<table width='100%' style='border-collapse:separate;border-spacing:8px;'>"
            "<tr>"
            "<td width='33%'><img src='https://picsum.photos/seed/wg-w/170/130' width='170' style='border-radius:6px;display:block;' alt='Women'><div style='padding-top:6px;font-size:13px;'>Women</div></td>"
            "<td width='33%'><img src='https://picsum.photos/seed/wg-m/170/130' width='170' style='border-radius:6px;display:block;' alt='Men'><div style='padding-top:6px;font-size:13px;'>Men</div></td>"
            "<td width='33%'><img src='https://picsum.photos/seed/wg-h/170/130' width='170' style='border-radius:6px;display:block;' alt='Home'><div style='padding-top:6px;font-size:13px;'>Home</div></td>"
            "</tr></table>"
            "<p style='margin:20px 0 0;'><a href='https://westgateretail.example/sale' style='background:#1f6feb;color:#fff;padding:12px 22px;border-radius:8px;text-decoration:none;font-weight:600;'>Shop the sale</a></p>",
            brand="Westgate Retail", accent="#bf3989", cid="wg-monsoon"),
    },
    {"h": 51, "cat": "Newsletters", "prio": "ignore", "unread": 0,
     "name": "Orbit Electronics", "addr": "deals@orbitelectronics.example",
     "subj": "Deals of the week — audio and wearables",
     "tldr": "Weekly promotional email for audio and wearable discounts.",
     "snippet": "Audio and wearables discounted this week.",
     "body": "DEALS OF THE WEEK  Audio up to 30% off  Wearables from Rs 2,999  https://orbitelectronics.example/c?t=71ac9f&u=ZGVhbHM"},
    {"h": 126, "cat": "Newsletters", "prio": "ignore", "unread": 0,
     "name": "Fitwave", "addr": "no-reply@fitwave.example",
     "subj": "We saved your spot — reactivate for ₹499",
     "tldr": "Gym membership reactivation offer.",
     "snippet": "Reactivate your membership for ₹499.",
     "body": "Your membership has been inactive for 60 days. Reactivate for Rs 499/month. https://fitwave.example/re?u=cc2"},
    {"h": 144, "cat": "Newsletters", "prio": "ignore", "unread": 0,
     "name": "Cloudkit", "addr": "billing@cloudkit.example",
     "subj": "Your free trial has ended",
     "tldr": "Free trial ended; the account has dropped to the free tier.",
     "snippet": "Trial ended, account moved to free tier.",
     "body": "Your 14-day trial has ended and your account has moved to the free tier. Upgrade any time: https://cloudkit.example/up"},
    {"h": 155, "cat": "Newsletters", "prio": "ignore", "unread": 0,
     "name": "Nomad Coffee Club", "addr": "roasts@nomadcoffee.example",
     "subj": "New roast drop — Ethiopia Guji",
     "tldr": "New coffee release announcement.",
     "snippet": "Ethiopia Guji, limited release.",
     "body": "New drop: Ethiopia Guji, washed, 250g. Limited to 400 bags. https://nomadcoffee.example/guji"},
    {"h": 194, "cat": "Social", "prio": "ignore", "unread": 0,
     "name": "LinkNet", "addr": "jobs@linknet.example",
     "subj": "8 jobs matching 'Backend Engineer, Bengaluru'",
     "tldr": "Automated job alert with eight listings.",
     "snippet": "8 new matches for your saved search.",
     "body": "8 new jobs match your saved search. https://linknet.example/jobs?s=be-blr&u=88f2a"},
    {"h": 205, "cat": "Work", "prio": "ignore", "unread": 0,
     "name": "Nordlight IT", "addr": "no-reply@it.nordlight.example",
     "subj": "Scheduled maintenance: VPN, Sunday 02:00–04:00",
     "tldr": "Planned VPN downtime on Sunday early morning.",
     "snippet": "VPN down Sunday 02:00-04:00.",
     "body": "Scheduled maintenance on the VPN gateway, Sunday 02:00-04:00 IST. No action needed. Do not reply to this address."},
]


# Draft bodies for the seeded draft proposals, keyed by the same subject fragment.
#
# Canned rather than generated: seeding stays fast, offline and deterministic, and a
# recording shows the same text every take. A draft row with no body is not a lesser
# proposal — it is one the executor now refuses outright — so these are required, not
# decorative.
DRAFT_BODIES: dict[str, str] = {
    "Singapore itinerary": (
        "Thanks, the itinerary looks good. Please leave the 17th open — I'd rather keep "
        "one day unscheduled. No changes needed to the rest."
    ),
    "Trek plan for October": (
        "Sounds good, I'm in for Kudremukh. Let me check my dates and confirm by the end "
        "of the week so you can book the permits in time."
    ),
}


# Proposals the agent has already made.
#
# Targets are keyed by a **unique fragment of the subject**, not by list position.
# Position-based keys silently rot the moment a message is inserted above them — the
# first draft of this file put "Photo tag notification" on a SQLite question — and the
# seeder raises on a fragment that matches zero or several subjects, so a mismatch is a
# crash at seed time rather than nonsense on a screen recording.
#
# (subject_fragment, type, status, rationale)
ACTIONS: list[tuple[str, str, str, str]] = [
    # --- label: everything with a real category and something at stake
    ("SW-4021 is confirmed",   "label", "proposed", "Flight confirmation with a departure date — filing under Travel keeps it with the itinerary."),
    ("Marina Bay loft",        "label", "proposed", "Check-in details for the same trip; belongs with the flight under Travel."),
    ("Q3 roadmap review",      "label", "proposed", "Direct request from your manager with a Wednesday deadline — Work."),
    ("PR #482",                "label", "proposed", "Review request blocking a teammate before Friday's freeze — Work."),
    ("Sign-in attempt blocked","label", "proposed", "Security alert from your bank; filing under Urgent so it stays visible."),
    ("due on 5 September",     "label", "proposed", "Card statement with a payment date — Finance."),
    ("INV-77401",              "label", "proposed", "Invoice with a return window open until 20 September — Receipts."),
    ("expires in 6 days",      "label", "proposed", "Domain expiry with a hard date six days out — Urgent."),
    ("Call me when you land",  "label", "proposed", "Personal message asking for a call — Personal."),

    # --- archive: 'ignore', older than a day, nothing addressed to you
    ("How Linear does onboarding", "archive", "proposed", "Marketing teardown, read-only content, no deadline."),
    ("Maps that lie on purpose",   "archive", "proposed", "Newsletter, unopened, older than 24 hours, nothing in it addressed to you."),
    ("The two-hour rule",          "archive", "proposed", "Weekly essay with no call to action; safe to file out of the inbox."),
    ("viewed your profile",        "archive", "proposed", "Profile-view notification from a no-reply address."),
    ("New replies to your question","archive","proposed", "Forum digest — the thread already has an accepted answer."),
    ("Deals of the week",          "archive", "proposed", "Promotional email; the sale ends before you return from Singapore."),
    ("We saved your spot",         "archive", "proposed", "Re-engagement marketing from a membership you let lapse."),
    ("New roast drop",             "archive", "proposed", "Product announcement, nothing to act on."),
    ("free trial has ended",       "archive", "proposed", "Trial-expiry notice; the account already dropped to the free tier."),

    # --- draft: a direct question from a human who can actually receive a reply
    ("Singapore itinerary",   "draft", "proposed", "Asks whether you want the free day on the 17th scheduled; a one-line reply closes it."),
    ("Trek plan for October", "draft", "proposed", "Direct question about dates from someone waiting on you before booking permits."),

    # --- the other three states, so the queue shows its full lifecycle on camera
    ("8 jobs matching",       "archive", "approved", "Automated job alert from a no-reply address; nothing here needs you."),
    ("Scheduled maintenance", "archive", "applied",  "Maintenance notice, no action required — already filed out of the inbox."),
    ("August 2026 statement", "label",   "rejected", "Proposed as Finance, but you keep bank statements in the inbox until reconciled."),
]
