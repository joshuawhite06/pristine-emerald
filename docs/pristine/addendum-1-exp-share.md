## Addendum: Early Exp. Share

Add the vanilla Gen III Exp. Share to the early-game Pokédex/Poké Ball event in Professor Birch's lab.

Desired flow:

```text
Receive Pokédex
↓
May/Brendan gives 5 Poké Balls
↓
May/Brendan also gives 1 Exp. Share
```

Implementation should reuse the existing lab script and add:

```c
giveitem ITEM_EXP_SHARE, 1
```

The Exp. Share should remain the normal Gen III held-item version. Do not convert it into a modern party-wide Exp. Share.

Because Emerald normally awards an Exp. Share later from Mr. Stone, adjust that later event so it does not unintentionally provide a second one unless multiple Exp. Shares are explicitly desired.

Preferred behavior:

```text
Early game:
May/Brendan → Exp. Share

Later Mr. Stone reward:
replace Exp. Share with 5 rare candies
```

No save-format changes are required.

This feature is optional and should be implemented only after the core QoL features unless specifically prioritized.

---

### Decision (2026-09-27): Professor Birch gives it

Birch gives the Exp. Share himself, right after the Pokédex, instead of
May/Brendan giving it with the Poké Balls (he's the one handing out
equipment, and the rival is standing right next to him):

```text
PROF. BIRCH: ...take this POKéDEX              (vanilla)
Obtained POKéDEX                                (vanilla)
PROF. BIRCH: The POKéDEX is a high-tech tool... (vanilla)
PROF. BIRCH: Oh, and one more thing.
             Take this, too!                    (new)
Obtained EXP. SHARE                             (new: giveitem ITEM_EXP_SHARE, 1)
PROF. BIRCH: Have a POKéMON hold the EXP. SHARE,
             and it'll get a share of the EXP.
             Points even if it doesn't battle!  (new)
May/Brendan gives 5 Poké Balls                  (vanilla, unchanged)
```

Birch's gift sets FLAG_RECEIVED_EXP_SHARE_FROM_BIRCH (vanilla's unused flag
0x20). When it's set, Mr. Stone doesn't give a second Exp. Share. A save from
vanilla that is already past the lab, or a full bag at the lab, leaves the
flag clear, and Mr. Stone gives the Exp. Share as in vanilla, so every player
gets exactly one.

### Decision (2026-09-27): Mr. Stone gives a starter instead of Rare Candies

The 5 Rare Candies are dropped. Mr. Stone gives the third Hoenn starter
instead (plan.md §11, "Decision: Mr. Stone gives the third starter"), plus the
Exp. Share when Birch's gift never happened.

Status: implemented (Birch's gift: `test/cases/test_exp_share.py`; Mr.
Stone: `test/cases/test_mr_stone.py`).
Test fixture: `test/fixtures/saves/route103-before-lab.sav`.
