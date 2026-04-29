import * as d3 from "d3";
import { BUILDERS, EDGES, PALETTE } from "./data.js";

const svg = d3.select("#graph");
const width = svg.node().clientWidth;
const height = 600;

const tooltip = document.createElement("div");
tooltip.id = "tooltip";
document.body.appendChild(tooltip);

const sim = d3
  .forceSimulation(BUILDERS)
  .force("link", d3.forceLink(EDGES).id((d) => d.id).distance(120))
  .force("charge", d3.forceManyBody().strength(-220))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("collide", d3.forceCollide(28));

const link = svg
  .append("g")
  .attr("class", "links")
  .selectAll("line")
  .data(EDGES)
  .enter()
  .append("line")
  .attr("class", "link")
  .attr("stroke-width", 1.5);

const node = svg
  .append("g")
  .attr("class", "nodes")
  .selectAll("circle")
  .data(BUILDERS)
  .enter()
  .append("circle")
  .attr("class", "node")
  .attr("r", 18)
  .attr("fill", (d) => PALETTE[d.cluster])
  .call(
    d3
      .drag()
      .on("start", (event, d) => {
        if (!event.active) sim.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) sim.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      })
  )
  .on("mouseenter", (event, d) => {
    tooltip.style.opacity = 1;
    tooltip.textContent = `${d.label} - ${d.skills.join(", ")}`;
  })
  .on("mousemove", (event) => {
    tooltip.style.left = `${event.pageX + 10}px`;
    tooltip.style.top = `${event.pageY + 10}px`;
  })
  .on("mouseleave", () => {
    tooltip.style.opacity = 0;
  });

const label = svg
  .append("g")
  .attr("class", "labels")
  .selectAll("text")
  .data(BUILDERS)
  .enter()
  .append("text")
  .attr("class", "label")
  .attr("text-anchor", "middle")
  .attr("dy", 32)
  .text((d) => d.label.split(" ")[0]);

sim.on("tick", () => {
  link
    .attr("x1", (d) => d.source.x)
    .attr("y1", (d) => d.source.y)
    .attr("x2", (d) => d.target.x)
    .attr("y2", (d) => d.target.y);
  node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
  label.attr("x", (d) => d.x).attr("y", (d) => d.y);
});

document.getElementById("count").textContent =
  `${BUILDERS.length} builders, ${EDGES.length} skill edges, ${PALETTE.length} clusters`;
