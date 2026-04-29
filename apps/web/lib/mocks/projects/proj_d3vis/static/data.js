// Six builders, three skill clusters. The cluster index drives node colour;
// the skills array drives the tooltip text.
export const BUILDERS = [
  { id: "aiko", label: "Aiko Tanaka", cluster: 0, skills: ["typescript", "three.js", "shaders"] },
  { id: "beni", label: "Beni Carter", cluster: 0, skills: ["d3", "data-vis", "svg"] },
  { id: "cherif", label: "Cherif Diallo", cluster: 1, skills: ["solidity", "viem", "web3"] },
  { id: "dilan", label: "Dilan Sahin", cluster: 1, skills: ["react", "tailwind", "css"] },
  { id: "esra", label: "Esra Yilmaz", cluster: 2, skills: ["canvas", "game-loops", "physics"] },
  { id: "faye", label: "Faye Robinson", cluster: 2, skills: ["typescript", "viz", "audio"] }
];

// Edges within and across clusters, simulating co-skill overlap.
export const EDGES = [
  { source: "aiko", target: "beni" },
  { source: "aiko", target: "faye" },
  { source: "cherif", target: "dilan" },
  { source: "esra", target: "faye" },
  { source: "beni", target: "dilan" }
];

export const PALETTE = ["#8347ff", "#22c55e", "#ff8585"];
