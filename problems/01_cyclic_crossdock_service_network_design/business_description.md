# Cyclic Freight Service Design with Cross-Dock Handling

A freight carrier publishes the same four-slot line-haul plan every week. Operating a listed leg uses one owned tractor and moves it to that leg's destination; tractors cannot be rented, created, or moved on unlisted deadheads. At most two owned tractors are available for this plan. A tractor may wait at a terminal without cost. Because the plan repeats, the same two physical tractors must cover every opened weekly departure through closed rotations; a longer rotation that needs three staggered tractors is not feasible.

One indivisible trailer-load is available at Origin O in slot 0 and must reach Destination D no later than the end of slot 3. At hub H, unloading, sorting, and reloading take one complete slot. Thus, freight arriving at H in slot 1 cannot board a departure in slot 1; its earliest eligible departure is slot 2. Choose the weekly service legs and the shipment path to minimize weekly operating cost. Return and rotation legs listed below close the next weekly cycle and are outside this shipment's delivery window.

Each listed leg may be operated at most once per week. Forward legs have capacity one for this shipment; return legs cannot carry this shipment.

| Leg | Owned-tractor movement in the periodic time-space network | Cost | Shipment eligible |
|---|---|---:|---|
| F1 | O at slot 0 to H at slot 1 | 2 | yes |
| R1 | H at slot 1 to O at slot 0 of the next week | 2 | no |
| F2 | H at slot 1 to D at slot 2 | 2 | yes |
| R2 | D at slot 2 to H at slot 1 of the next week | 2 | no |
| F3 | H at slot 2 to D at slot 3 | 10 | yes |
| R3 | D at slot 3 to H at slot 2 of the next week | 10 | no |
| F4 | O at slot 0 to D at slot 3 | 7.5 | yes |
| R4 | D at slot 3 to O at slot 0 of the next week | 7.5 | no |
