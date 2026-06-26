"""
Graph Visualisation Generator
Reads cdr_communities.json + ipdr_communities.json
Outputs two standalone HTML graph files you can open in any browser.

Install:
  pip install pyvis

Run:
  python generate_graph.py

Output:
  cdr_graph.html   — CDR community network
  ipdr_graph.html  — IPDR IP community network
"""

import json
import os
from pyvis.network import Network

# ── COLOUR PALETTES ──────────────────────────────────────────────
COMMUNITY_COLORS = [
    "#4f7cff","#e24b4a","#1d9e75","#ef9f27","#a855f7",
    "#06b6d4","#f43f5e","#84cc16","#f97316","#8b5cf6",
    "#ec4899","#14b8a6","#eab308","#3b82f6","#10b981",
    "#f59e0b","#6366f1","#ef4444","#22c55e","#0ea5e9"
]

RISK_COLORS = {
    "HIGH":   "#e24b4a",
    "MEDIUM": "#ef9f27",
    "MED":    "#ef9f27",
    "LOW":    "#1d9e75",
    None:     "#545d75"
}

def comm_color(comm_id):
    return COMMUNITY_COLORS[comm_id % len(COMMUNITY_COLORS)]

def risk_color(label):
    return RISK_COLORS.get(label, RISK_COLORS[None])


# ── CDR GRAPH ────────────────────────────────────────────────────

def build_cdr_graph(communities: list[dict], output: str = "cdr_graph.html", max_members: int = 60):
    """
    Nodes:
      - Community hub nodes (diamond shape, larger)
      - User nodes (circle, sized by centrality)
      - Leader nodes (star border)
    Edges:
      - User → Community hub (thin, community colour)
      - Bridge edges between hubs (thick dashed, orange)
    """
    net = Network(
        height="100vh", width="100%",
        bgcolor="#0f1117", font_color="#e8eaf0",
        heading="CDR Community Network"
    )
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=200, spring_strength=0.04)

    added_nodes = set()

    for comm in communities:
        cid = comm["community_id"]
        color = comm_color(cid)
        r_color = risk_color(comm.get("risk_label"))
        leader = str(comm.get("leader", ""))
        members = [str(m) for m in comm.get("members", [])][:max_members]

        # Hub node
        hub_id = f"hub_{cid}"
        risk_label = comm.get("risk_label", "N/A")
        risk_score = comm.get("risk_score", "N/A")
        hub_title = (
            f"<b>Community {cid}</b><br>"
            f"Members: {comm['size']}<br>"
            f"Density: {comm['density']}<br>"
            f"Leader: {leader}<br>"
            f"Risk: {risk_label} ({risk_score})<br>"
            f"Interactions: {comm.get('total_interactions','N/A')}"
        )
        net.add_node(
            hub_id,
            label=f"C{cid}\n({comm['size']} members)",
            shape="diamond",
            color={"background": color, "border": "#ffffff"},
            size=35,
            borderWidth=3,
            title=hub_title,
            font={"size": 14, "bold": True}
        )
        added_nodes.add(hub_id)

        # Member nodes
        for member in members:
            node_id = f"user_{member}"
            is_leader = member == leader

            member_title = (
                f"<b>User {member}</b><br>"
                f"Community: {cid}<br>"
                f"{'⭐ Leader' if is_leader else 'Member'}<br>"
                f"Risk: {risk_label}"
            )

            if node_id not in added_nodes:
                net.add_node(
                    node_id,
                    label=f"★{member}" if is_leader else member,
                    shape="star" if is_leader else "dot",
                    color={"background": color, "border": "#ffffff" if is_leader else color},
                    size=20 if is_leader else 12,
                    borderWidth=3 if is_leader else 1,
                    title=member_title,
                    font={"size": 10}
                )
                added_nodes.add(node_id)

            net.add_edge(
                hub_id, node_id,
                color=color + "80",
                width=1,
                arrows=""
            )

    # Bridge edges between hubs
    drawn_bridges = set()
    for comm in communities:
        cid = comm["community_id"]
        for bridge in comm.get("bridge_nodes", []):
            for ext_comm in bridge.get("external_communities", []):
                if ext_comm is None:
                    continue
                key = tuple(sorted([cid, ext_comm]))
                if key not in drawn_bridges:
                    drawn_bridges.add(key)
                    net.add_edge(
                        f"hub_{cid}", f"hub_{ext_comm}",
                        color="#ef9f27",
                        width=4,
                        dashes=True,
                        title=f"Bridge via User {bridge['node']} ({bridge.get('external_connections','')} connections)",
                        arrows=""
                    )

    net.show_buttons(filter_=["physics"])
    net.save_graph(output)
    print(f"CDR graph saved → {output}  ({len(net.nodes)} nodes, {len(net.edges)} edges)")


# ── IPDR GRAPH ───────────────────────────────────────────────────

def build_ipdr_graph(communities: list[dict], output: str = "ipdr_graph.html", max_ips: int = 40):
    """
    Nodes:
      - Cluster hub nodes (large diamond)
      - IP nodes (small circles, coloured by community)
    Edges:
      - IP → hub (thin)
    """
    net = Network(
        height="100vh", width="100%",
        bgcolor="#0f1117", font_color="#e8eaf0",
        heading="IPDR IP Community Network"
    )
    net.barnes_hut(gravity=-5000, central_gravity=0.2, spring_length=150, spring_strength=0.05)

    for comm in communities:
        cid = comm["community_id"]
        color = comm_color(cid)
        ips = [str(ip) for ip in comm.get("ips", [])][:max_ips]
        dominant_app = comm.get("dominant_app", "unknown")
        risk_label = comm.get("risk_label", "N/A")
        r_color = risk_color(comm.get("risk_label"))

        hub_title = (
            f"<b>IP Cluster {cid}</b><br>"
            f"IPs: {comm['size']}<br>"
            f"Dominant App: {dominant_app}<br>"
            f"High-Risk Ratio: {comm.get('high_risk_ratio', 'N/A')}<br>"
            f"Total Flows: {comm.get('total_flow_count', 'N/A')}<br>"
            f"Risk: {risk_label}"
        )

        # App emoji
        app_emoji = {
            "youtube": "▶️", "facebook": "👤", "http": "🌐",
            "google": "🔍", "ssl": "🔒", "tor": "🧅",
            "whatsapp": "💬", "skype": "📞", "dropbox": "📦"
        }.get(dominant_app.lower(), "📡")

        net.add_node(
            f"hub_{cid}",
            label=f"{app_emoji} Cluster {cid}\n{dominant_app}\n({comm['size']} IPs)",
            shape="diamond",
            color={"background": color, "border": r_color},
            size=40,
            borderWidth=4,
            title=hub_title,
            font={"size": 13, "bold": True}
        )

        for ip in ips:
            node_id = f"ip_{ip}"
            net.add_node(
                node_id,
                label=ip,
                shape="dot",
                color={"background": color, "border": color},
                size=8,
                title=f"IP: {ip}<br>Cluster: {cid}<br>App: {dominant_app}",
                font={"size": 8}
            )
            net.add_edge(f"hub_{cid}", node_id, color=color + "60", width=1, arrows="")

    net.show_buttons(filter_=["physics"])
    net.save_graph(output)
    print(f"IPDR graph saved → {output}  ({len(net.nodes)} nodes, {len(net.edges)} edges)")


# ── MAIN ─────────────────────────────────────────────────────────

def main():
    # Load CDR communities
    cdr_path = "cdr_communities.json"
    ipdr_path = "ipdr_communities.json"

    if not os.path.exists(cdr_path):
        print(f"ERROR: {cdr_path} not found. Run the pipeline first.")
        return

    if not os.path.exists(ipdr_path):
        print(f"ERROR: {ipdr_path} not found. Run the pipeline first.")
        return

    with open(cdr_path) as f:
        cdr_communities = json.load(f)

    with open(ipdr_path) as f:
        ipdr_communities = json.load(f)

    print(f"Loaded {len(cdr_communities)} CDR communities")
    print(f"Loaded {len(ipdr_communities)} IPDR communities")
    print()

    build_cdr_graph(cdr_communities,  output="cdr_graph.html",  max_members=60)
    build_ipdr_graph(ipdr_communities, output="ipdr_graph.html", max_ips=40)

    print()
    print("Done! Open these files in your browser:")
    print("  cdr_graph.html")
    print("  ipdr_graph.html")


if __name__ == "__main__":
    main()
