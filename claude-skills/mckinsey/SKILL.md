---
name: mckinsey
description: Transform strategic documents into layered "onion-style" McKinsey reports with auto-detected frameworks (Porter's 5 Forces, SWOT, TAM/SAM/SOM, etc.).
---

# McKinsey Digest

Transform strategic documents into layered "onion-style" McKinsey reports with auto-detected frameworks.

## When to Use
Use when user provides a document path and wants to:
- Create executive summaries
- Extract strategic insights
- Generate consulting-style analysis
- Digest long research/strategy documents

---

## Instructions

### Input
$ARGUMENTS should contain the path to a document file (.txt, .md, .pdf)

If no path provided, ask: "What document would you like me to analyze?"

### Step 1: Read & Classify

1. Read the full document using the Read tool
2. Classify the document type:
   - Market analysis / competitive landscape
   - Strategy memo / business case
   - Research report / white paper
   - Due diligence / M&A analysis
   - Technical/product analysis
   - Other (describe)

3. Extract key elements:
   - Central thesis/argument
   - Key entities (companies, products, markets)
   - Quantitative data points
   - Strategic frameworks already present
   - Major themes/sections

### Step 2: Framework Detection

Scan content for signals and select 2-3 most applicable frameworks:

| Signal | Framework |
|--------|-----------|
| Multiple competitors, market dynamics | Porter's 5 Forces |
| Strengths/weaknesses discussion | SWOT |
| Market sizing, opportunity | TAM/SAM/SOM |
| Platform dynamics, ecosystems | Network Effects |
| Buy/build/partner decisions | Make vs Buy Matrix |
| Risk/reward tradeoffs | 2x2 Positioning Matrix |
| Value creation chain | Value Chain Analysis |
| Acquisition patterns | M&A Integration Playbook |
| Startup positioning | Defensibility Framework |

**Rule**: Only apply frameworks that genuinely fit. Don't force.

### Step 3: Generate 4-Layer Report

Create the following sections:

---

#### LAYER 1: EXECUTIVE SKIM (30 sec read)

**Thesis**: [Single sentence capturing the core insight]

**Three Takeaways**:
1. [What matters]
2. [So what - implication]
3. [Now what - action]

**Key Number**: [Most impactful stat with context]

---

#### LAYER 2: KEY INSIGHTS (2 min read)

**Situation**: [Current state - what is]
**Complication**: [Tension/challenge - but...]
**Resolution**: [Path forward - therefore...]

**Strategic Framework**:
[Render the most applicable framework as ASCII diagram or table]

**Core Findings**:
1. [Finding with evidence]
2. [Finding with evidence]
3. [Finding with evidence]
4. [Finding with evidence]
5. [Finding with evidence]

---

#### LAYER 3: TECHNICAL ANALYSIS (5-10 min read)

For each major theme in the document:

**[Theme Name]**

*Key Points*:
- Point with supporting data
- Point with supporting data

*Implications*:
- What this means for [stakeholder]

*Framework Application*:
[Apply relevant framework with specifics from document]

[Repeat for 3-5 major themes]

**Data Summary**:
| Metric | Value | Source/Context |
|--------|-------|----------------|
| ... | ... | ... |

---

#### LAYER 4: FULL REFERENCE

**Complete Content Map**:
[Hierarchical outline of all document content]

**Entity Index**:
- Companies mentioned: [list]
- Products/services: [list]
- Markets/segments: [list]
- Key people/roles: [list]

**Glossary**:
| Term | Definition |
|------|------------|
| ... | ... |

**Key Quotes**:
> "Quote 1" - Context

**Cross-References**:
- [Topic A] relates to [Topic B] because...

---

### Step 4: Save & Present

1. Save the full report to: `{original-filename}-digest.md` in the same directory as source
2. Display LAYER 1 to user immediately in the chat
3. Tell user: "Full 4-layer report saved to {path}. Would you like me to expand on any section?"

---

## Output Format Notes

- Use clean markdown formatting
- ASCII diagrams for frameworks (no images)
- Tables for structured data
- Bullet points for findings
- Block quotes for key excerpts
- Headers with clear layer markers

## Example ASCII Frameworks

### 2x2 Matrix
```
                    HIGH VALUE
                        |
         +--------------+--------------+
         |              |              |
         |   Invest     |   Prioritize |
         |   Carefully  |   Now        |
         |              |              |
LOW      +--------------+--------------+ HIGH
EFFORT   |              |              | EFFORT
         |   Quick      |   Deprioritize|
         |   Wins       |   or Partner |
         |              |              |
         +--------------+--------------+
                        |
                    LOW VALUE
```

### Value Chain
```
[Supplier] --> [Inbound] --> [Operations] --> [Outbound] --> [Marketing] --> [Service]
                                    |
                        +-----------+-----------+
                        |           |           |
                    [Infra]    [HR/Tech]   [Procurement]
```

### Network Effects Map
```
     +-------+
     | Users |<--------+
     +---+---+         |
         |             |
         v             |
    +----+----+        |
    | Content |        |
    +----+----+        |
         |             |
         v             |
   +-----+-----+       |
   | Advertisers|------+
   +-----------+
```
