# C07 - Rack-scale and facilities readiness

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (sizing calculator) + workshop with facilities | 3 h + workshop | FAC, FIN, CMP | Target GPU count from `CMP-03`/`CMP-04`. Dell spec sheets or EIPT output for the chosen servers. |

AI racks draw several times what a normal enterprise rack does, so power and cooling often decide the design more than the servers do. Dell offers Integrated Rack Scalable Systems (IRSS): racks built, cabled and tested in the factory, including liquid-cooled options. This lab turns a GPU target into numbers the facilities team can check. **The default power figures in `site.yaml` are placeholders, not Dell data.** Take node power from the Dell Enterprise Infrastructure Planning Tool (EIPT) or the spec sheet for your exact configuration.

## Steps

### Step 1 - Gather inputs
From the platform team: target GPU count, GPUs per node, server model and configuration, nodes per rack, switches per rack, storage racks.
From facilities: power per rack position today and the maximum (`FAC-01`), cooling type and limits (`FAC-02`), total IT kW available over 36 months (`FAC-03`), PUE.

### Step 2 - Run the calculator
Edit `labs/env/facilities/site.yaml`, then:
```bash
cd labs/env && python3 facilities/size.py
```
Expected with the shipped placeholders: `256 GPUs -> 32 nodes in 8 compute racks`, `compute rack: 49.0 kW max`, two `GAP:` lines (rack power above 40 kW and above the 30 kW air-cooling limit).

### Step 3 - Close the gaps
Try the options and record the result of each run:
1. Fewer nodes per rack (`nodes_per_rack: 3`): more racks and floor space, fewer kW per rack.
2. Liquid cooling (`cooling: dlc`): removes the air limit gap. Record what DLC needs (secondary loop, CDU, water temperature, leak detection).
3. More power per rack (`max_kw_per_rack: 60`): ask facilities what that costs and how long it takes.
4. Power capping (`FAC-06`): set `node_typical_pct` to the cap you are willing to enforce, and note the expected training slowdown.

### Step 4 - Site-readiness checklist (workshop)
Walk through with facilities and record an owner and date for each line:
- Power: feeds per rack (A/B), PDU type and outlets (C19/C20 count), 3-phase voltage, UPS and generator coverage.
- Cooling: air (inlet temperature, hot/cold aisle containment), rear-door heat exchangers, DLC loop and CDU.
- Space and weight: floor loading (a full GPU rack can exceed 1,000 kg), door heights and lift capacity for pre-built IRSS racks (`FAC-04`), delivery path.
- Network: cable trays for back-end fabric, fibre count to the storage and core rooms.
- Lead times: power and cooling upgrades usually take longer than server delivery.

### Step 5 - Sustainability and end of life
Record PUE target, carbon reporting needs and heat-reuse options (`FAC-05`), and asset disposal / data sanitisation requirements (`FAC-07`).

## Verify
- [ ] `size.py` output saved for the baseline and each option.
- [ ] `FAC-01`..`FAC-04` have numbers, not "TBD".
- [ ] Every checklist line has an owner and a date.

## Record for the standards
`FAC-01` kW per rack. `FAC-02` cooling. `FAC-03` total power and space. `FAC-04` IRSS / pre-built racks. `FAC-06` power capping. `FAC-05`, `FAC-07` sustainability and disposal. `FIN-05` expansion trigger.

## Cleanup
None. Keep `site.yaml` versions in Git as the sizing record.
