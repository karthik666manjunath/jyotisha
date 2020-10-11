## Command
From `pytest -k tests.spatio_temporal.test_annual.test_timing` on vvasuki's machine.

## Results
run time: 32s
```
            compute_angas: 20226.73ms for      1 calls
  update_festival_details: 5687.07ms for      2 calls
assign_festivals_from_rules: 3169.96ms for      2 calls
          assign_festival:    0.01ms for  500780 calls
assign_tithi_yoga_nakshatra_fest:    0.07ms for  43848 calls
                   __eq__:    0.00ms for  942603 calls
             dump_to_file:  508.51ms for      1 calls
           set_rule_dicts:  507.88ms for      1 calls
                  __add__:    0.01ms for  59969 calls
                  __sub__:    0.00ms for  78473 calls
                   __lt__:    0.01ms for  37364 calls
                   __gt__:    0.00ms for   5095 calls
                 __init__:    0.00ms for   2544 calls
```

## Comment:
