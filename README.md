# ⚛️ Quantum Atom Simulator

### See the Invisible.

You've seen the atom drawn a thousand times — a ball in the middle, some smaller balls looping around it like tiny planets. It's a lie we tell in grade school because the truth doesn't fit on a chalkboard.

The truth is stranger and more beautiful: electrons aren't balls on rails. They're probability clouds — fuzzy, glowing regions of *maybe* — and the "orbits" you were taught are really shapes called **orbitals**, sculpted by the math of quantum mechanics. Zoom into the nucleus at the center, and it gets stranger still: protons and neutrons held together by a force so powerful it can only be described as an endless exchange of ghost particles, all the way down to quarks bound by gluons.

**Quantum Atom Simulator** puts that entire universe in your browser. No installs, no plugins, no PhD required — just drag, zoom, and watch matter reveal itself.

![Quantum Atom Simulator Preview](images/preview.png)

## 🌐 Live Demo

**[Launch Quantum Atom Simulator →](https://nazat02.github.io/Quantum-Atom/)**

---

## 🌟 What's Inside

The project has three parts, wired together, each with matching light and dark themes:

1. **Landing page** (`index_dark.html` / `index_light.html`) — the "See the Invisible" intro page, explaining what orbitals actually are before you launch the tool. `index.html` auto-redirects here.
2. **Atom + Molecule Simulator** (`simulator_dark.html` / `simulator_light.html`) — the main tool, reached via the landing page's "Launch" button.
3. **Nucleus Explorer** (`nucleus_explorer.html` / `nucleus_explorer_light.html`) — reached via a button inside the Simulator.

### ⚛️ The Atom Simulator
A real-time 3D renderer that builds **accurate s, p, and d orbital shapes** from genuine quantum probability distributions, using custom GLSL shaders for tens of thousands of glowing points per cloud.

- **The full periodic table, all 118 elements**, from Hydrogen to Oganesson, instantly selectable with live search
- **A living data panel**, atomic number, full electron configuration, period, group, and orbital info that update as you explore
- **A 3D nucleus you can actually see**, protons (red) and neutrons (blue) packed with a Fibonacci sphere distribution and real internal lighting, not a flat sprite
- **Excited State mode**, promotes electrons to higher orbitals and shows the transition path in the data panel (atoms only, not available in molecule mode)
- **Ultra Mode**, switches orbitals from point-cloud rendering to mesh-based surfaces with a Fresnel shader (transparent center, glowing rim), for a smooth "glass bubble" look with zero point grain
- **Smooth Orbitals mode**, a softer point-cloud alternative to the default detailed/grainy rendering, plus a **Real Image Mode** styled after real atomic imaging
- **A Cartesian grid overlay** for anyone who wants to see the geometry, not just the glow
- **Antimatter Mode**, charge-conjugate any element or molecule on the fly: electrons render as positrons, protons and neutrons render as antiprotons and antineutrons, with identical orbital geometry to the matter version. The UI retints into its own neon pink/violet and electric-blue color model, the data panel relabels live (ANTIPROTONS / ANTINEUTRONS / POSITRONS, an ANTI- prefix on the name, overline antimatter notation on the symbol), and nucleus lighting shifts to match

### 🧪 Molecule Mode
Flip the switch from **Atoms** to **Molecules** inside the Simulator and watch individual electron clouds fuse into real chemical structures, **52 curated molecules**, from simple diatomics like H₂ and O₂ to shapes every chemistry student has drawn by hand: bent H₂O, trigonal pyramidal NH₃, tetrahedral CH₄, trigonal bipyramidal PF₅, octahedral SF₆, and more. Bond angles and geometry are derived from real VSEPR theory, not hard-coded guesses, so the shapes you see are the shapes molecules actually take. Antimatter Mode works here too, charge-conjugating every atom in the molecule at once.

### 🔬 Nucleus Explorer
A companion tool that does one thing no textbook diagram can: **lets you zoom in forever.**

Start at the whole nucleus and keep scrolling in. First the individual protons and neutrons resolve into view, with toggleable **pion exchange** and **gluon field** overlays showing the forces holding them together. Keep going, and nucleons dissolve into **quarks bound by gluons**, the actual bottom of the visible matter stack. You can step through elements with previous/next controls, jump straight to one from the element picker, and there's a built-in legend and help panel for what you're looking at.

---

## 🛠️ Technologies

- **Three.js (r128)** for all 3D rendering
- **Custom GLSL shaders**, high-performance point clouds with additive blending and dynamic per-point sizing, plus mesh-based Fresnel shading for Ultra Mode
- **Vanilla JavaScript**, every tool is a single self-contained HTML file, no build step, no bundler, no dependencies to install

---

## 🎮 Controls

### Atom / Molecule Simulator

| Action                       | Input                              |
|-------------------------------|-------------------------------------|
| Rotate Atom                   | Mouse drag / Touch drag            |
| Zoom                           | Scroll wheel / Pinch gesture       |
| Cycle Elements                 | Left / Right Arrow keys            |
| Reset View                     | **RESET** button                   |
| Select Element                 | Click element in left panel        |
| Search Elements                 | Search bar in the element panel    |
| Switch Atoms / Molecules        | **ATOMS / MOLECULES** mode toggle  |
| Toggle Antimatter Mode          | **ANTIMATTER** button              |
| Toggle Real Image Mode          | **REAL IMAGE MODE** button         |
| Toggle Cartesian Grid           | **CARTESIAN GRID** button          |
| Toggle Smooth Orbitals          | **SMOOTH ORBITALS** button         |
| Toggle Ultra Mode               | **ULTRA MODE** button              |
| Toggle Excited State            | **EXCITED STATE** button (atoms only) |
| Open element/molecule browser   | **EXPLORE** tab                    |
| Open Data Panel                 | **DATA** tab                       |
| Open Nucleus Explorer           | Nucleus icon button in the toolbar |

### Nucleus Explorer

| Action                      | Input                               |
|------------------------------|--------------------------------------|
| Zoom nucleus → quark scale   | Zoom slider / Scroll / Pinch         |
| Previous / next element      | **‹ ›** nav buttons                  |
| Jump to an element           | **ELEMENTS** button                  |
| Toggle pion exchange overlay | **PIONS** toggle                     |
| Toggle gluon field overlay   | **GLUONS** toggle                    |
| Reset camera                 | **RESET** toggle                     |
| Show color legend            | Legend button                        |
| Controls help                | **?** button                         |

Fully responsive, desktop gets full side panels, mobile gets touch-friendly bottom sheets.

**Pro Tips:**
- Double-click the atom to snap back into auto-spin
- Try **Real Image Mode** + **Smooth Orbitals** together for the most cinematic view, or **Ultra Mode** for a glassy, grain-free look
- In Nucleus Explorer, just keep scrolling in, the physics changes as you go
- Flip **ANTIMATTER MODE** on any element or molecule to see its charge-conjugated counterpart, same geometry, opposite matter

---

## 📋 Roadmap

Actively growing. Up next:

- Probability density isosurfaces
- Bohr model toggle for side-by-side comparison with the classic (wrong) picture
- Ionization states and electron transitions
- High-resolution screenshot export
- Performance / quality presets
- Electron spin visualization
- WebXR augmented reality support

---

## 🚀 Getting Started

Because every tool is a single HTML file, there's nothing to build and nothing to install.

1. **Clone the repository**
   ```bash
   git clone https://github.com/nazat02/Quantum-Atom.git
   ```
2. **Open it**
   ```bash
   cd Quantum-Atom
   open index_dark.html   # or index_light.html
   ```
   Any modern browser works, just double-click the file, or serve the folder with any static file server. From there, use "Launch" to reach the Simulator, and the nucleus icon inside the Simulator to reach the Nucleus Explorer.

---

## 📄 License

Released under **[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)** (Attribution-ShareAlike). Use it, remix it, build on it, even commercially, as long as you credit **nazat02** and release your version under this same license. See `LICENSE.txt` for the full terms.

---

### Why this exists

Most atom visualizers are either scientifically hand-wavy cartoons or dense simulation software that only a physicist could love. Quantum Atom Simulator was built to sit in the gap, real quantum-derived geometry, real chemistry, real nuclear physics, wrapped in something you can hand to a curious 12-year-old or a chemistry professor and have both walk away impressed.

Drag. Zoom. See what you're actually made of.
