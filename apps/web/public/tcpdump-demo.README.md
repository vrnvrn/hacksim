# tcpdump-demo asset

The "Run it locally" panel on `/docs` is wired to render an asciinema recording of `tcpdump` during a real `make demo` run when a file named `tcpdump-demo.cast` lives next to this README. The component (`apps/web/components/RunItLocally.tsx`) checks for the asset at build time and renders a `<asciinema-player>` element pointed at `/tcpdump-demo.cast`; if the file is absent the panel renders without that section.

To record one:

```bash
brew install asciinema   # or apt install asciinema on Linux
asciinema rec -t "HackSim AXL traffic" --max-wait 1 -i 2 \
  /tmp/tcpdump-demo.cast \
  -c "sudo tcpdump -i lo0 -n 'tcp port 9100 or tcp port 7000' | head -40"

# Stop with C-d after about 30 seconds. Then in another terminal:
make demo
# Hit Spin up sim. The recording captures envelopes flying between
# AXL nodes during the bounty / build / judging phases.
```

Move `/tmp/tcpdump-demo.cast` into this directory and rebuild the
frontend.

The recording sits in `apps/web/public/` so it ships as a static asset
under the deploy. Embed instructions for asciinema-player live in the
[asciinema docs](https://docs.asciinema.org/manual/player/embedding/).
