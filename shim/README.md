# outboard (deprecated)

This package was renamed to [out-of-band](https://pypi.org/project/out-of-band/).

This final release exists so `pip install outboard` keeps working: it installs
`out-of-band` and leaves the old `outboard` command as an alias for `oob`.

New projects should install `out-of-band` and use `oob`:

```bash
pip install out-of-band
oob --version
```

The receipt format did not change. Receipts signed by `outboard` still verify;
the verifier accepts both `outboard/<version>` and `oob/<version>` in the `tool`
field.
