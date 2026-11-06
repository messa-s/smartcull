#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge

#set text(font: "Times New Roman")

#set page(
  paper: "a4",
  margin: (top: 1.2in, bottom: 1.2in, left: 1in, right: 1in),

  // Line at the top of every page
  header: line(length: 100%, stroke: 1pt),

  // Line at the bottom (page number removed)
  footer: line(length: 100%, stroke: 1pt),
)

// ---------------- Level 0 ----------------
#diagram(
  spacing: (5em, 2em),
  edge-stroke: 1pt,
  {
    node((0,0), "User", stroke: 1pt + black, shape: rect, height: 5em, width: 10em, name: <user>)
    node((1.5,0), "smartcull", stroke: 1pt, radius: 4em, name: <proc>)
    node((3,0), "File System", stroke: 1pt + black, shape: rect, height: 5em, width: 10em, name: <user2>)

    edge(<user.north>, <proc.north-west>, "-|>", [Photos/videos, search query], bend: 75deg, snap-to: (none, none))
    edge(<proc.south-west>, <user.south>, "-|>", [Matches, timestamps], bend: 75deg, snap-to: (none, none))
    edge(<user2.north>, <proc.north-east>, "-|>", [Media files], bend: -75deg, snap-to: (none, none))
    edge(<proc.south-east>, <user2.south>, "-|>", [Exported clips, folders], bend: -75deg, snap-to: (none, none))
  }
)

#align(center)[
  #text(12pt, style: "italic")[Figure 1: Level 0 DFD of SmartCull AI]
  #v(2em)
]

#pagebreak()

// ---------------- Level 1 ----------------
#align(center)[
  #text(10pt)[
    #diagram(
      spacing: (7em, 4em),
      edge-stroke: 1pt,
      node-stroke: 1pt,
      {
        // External entity
        node((1,0), [User], shape: rect, width: 8em, height: 3em, name: <user>)

        // Processes (one per module)
        node((1,1), align(center)[*4.0* \ User Interface \ and Export], shape: circle, name: <p4>)
        node((1,2), align(center)[*3.0* \ Backend \ Controller], shape: circle, name: <p3>)
        node((0,3), align(center)[*1.0* \ Import and \ Preprocessing], shape: circle, name: <p1>)
        node((2,3), align(center)[*2.0* \ Models and \ Processing], shape: circle, name: <p2>)

        // Data stores
        node((0,4), [D1: Media Files], shape: rect, width: 8em, height: 3em, name: <d1>)
        node((2,1), [D2: Export Folders], shape: rect, width: 8em, height: 3em, name: <d2>)

        // User <-> Interface
        edge(<user>, <p4>, "-|>", [Actions], bend: 20deg)
        edge(<p4>, <user>, "-|>", [Results], bend: 20deg)

        // Interface <-> Controller
        edge(<p4>, <p3>, "-|>", [Requests], bend: 20deg)
        edge(<p3>, <p4>, "-|>", [Ranked results], bend: 20deg)

        // Interface -> Export folders
        edge(<p4>, <d2>, "-|>", [Selected files])

        // Controller -> Import -> Models -> Controller
        edge(<p3>, <p1>, "-|>", [Import request])
        edge(<p1>, <p2>, "-|>", [Media list, frames])
        edge(<p2>, <p3>, "-|>", [Scores, search results])

        // Media files -> Import
        edge(<d1>, <p1>, "-|>", [Photos, videos])
      }
    )
  ]
]

#align(center)[
  #text(12pt, style: "italic")[Figure 2: Level 1 DFD of SmartCull AI]
]
