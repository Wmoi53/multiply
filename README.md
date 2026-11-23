# multiply
agent multi tasking for a single project in 60days

## Projects

### `singing-tree/` — The Singing Tree landing page
A landing page for a fictional singing Christmas tree and its choir at Marina Bay. Eight agents run the production. No build step and no dependencies: open `singing-tree/index.html` in a browser.

- **Stage:** a live canvas render of a 42 m tree. Drag to orbit it, tap to send a spark up the trunk.
- **Console:** lamps, twinkle, bloom, palette, snow, wind, haze, choir bus, reverb and SATB sections. You can export the current frame as a PNG or the setup as a JSON cue sheet.
- **Agents:** drag or tap eight agents onto eight zones. A vacant zone goes dark on stage and drops its cues.
- **Choir:** six carols arranged as SATB and sung live with Web Audio (formant-filtered voices and a synthesised reverb).
- **Run of show:** a 56-second, 7-cue timeline with a scrubber. Each cue moves the console settings.
- **Visit:** a booking flow with validation. Bookings are saved in the browser's localStorage, and you can download a pass.
