## Command
From `pytest -k tests.spatio_temporal.test_annual.test_timing` on vvasuki's machine.

## Results
run time: 19.3s
```
  update_festival_details: 5569.62ms for      2 calls
            compute_angas: 7412.40ms for      1 calls
assign_festivals_from_rules: 3133.03ms for      2 calls
  get_all_angas_in_period:    2.98ms for   1910 calls
          assign_festival:    0.01ms for  500780 calls
assign_tithi_yoga_nakshatra_fest:    0.08ms for  43848 calls
                   __eq__:    0.00ms for  906323 calls
                     find:    7.00ms for    107 calls
           set_rule_dicts:  507.60ms for      1 calls
             dump_to_file:  501.23ms for      1 calls
                  __sub__:    0.00ms for  58788 calls
                  __add__:    0.01ms for  49984 calls
                   __lt__:    0.01ms for  13655 calls
                 __init__:    0.00ms for   2519 calls
                   __gt__:    0.00ms for   1071 calls
```

## Comment:
