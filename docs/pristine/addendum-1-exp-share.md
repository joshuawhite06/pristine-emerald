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
