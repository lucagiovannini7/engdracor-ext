#!/usr/bin/env python3
"""Convert ECCO-TCP TEI XML files to DraCor-compliant TEI-XML.

Usage:
    python convert_to_dracor.py

Reads every *.xml file in xml/ (skipping xml/unfixable/) and writes
a DraCor-compatible TEI file to tei/ named {surname}-{title}.xml.
"""

import copy
import glob
import os
import re
import traceback

from lxml import etree

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
XML_DIR     = os.path.join(SCRIPT_DIR, "xml")
TEI_DIR     = os.path.join(SCRIPT_DIR, "tei")
UNFIXABLE   = os.path.join(XML_DIR, "unfixable")

# ── Namespaces ─────────────────────────────────────────────────────────────────
NS   = "http://www.tei-c.org/ns/1.0"
XMNS = "http://www.w3.org/XML/1998/namespace"


def Q(tag: str) -> str:
    return f"{{{NS}}}{tag}"


def QX(attr: str) -> str:
    return f"{{{XMNS}}}{attr}"


PI_LINE = (
    '<?xml-model href="https://dracor.org/schema.rng" '
    'type="application/xml" '
    'schematypens="http://relaxng.org/ns/structure/1.0"?>'
)

# ── String helpers ─────────────────────────────────────────────────────────────

def slugify(s: str) -> str:
    """Convert a string to a hyphen-separated slug."""
    s = s.strip().lower()
    s = re.sub(r"[''`'\u2018\u2019]", "", s)   # remove apostrophes
    s = re.sub(r"[^a-z0-9]+", "-", s)           # non-alphanumeric → hyphen
    return re.sub(r"-+", "-", s).strip("-")


def get_text(el) -> str:
    """Return all text content of an element (including children), stripped."""
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


# ── Speaker helpers ────────────────────────────────────────────────────────────

def speaker_to_xml_id(raw: str) -> str:
    """
    Normalise a raw speaker string to a valid XML NCName.
    'Colin.'       → 'colin'
    'La Jeu.'      → 'la_jeu'
    '1 Lead.'      → 'lead-1'      (digit prefix moved to end)
    '1st. Foot.'   → 'foot-1st'
    '2d. Foot.'    → 'foot-2d'
    """
    s = raw.strip().lower()
    s = re.sub(r"[.\s,;:!?()\[\]'\"]+", "_", s)
    s = s.strip("_")
    s = re.sub(r"_+", "_", s)
    # NCNames cannot start with a digit — move the leading ordinal/number to the end
    if s and s[0].isdigit():
        m = re.match(r'^(\d+(?:st|nd|rd|th|d)?)_?(.*)', s)
        if m:
            num, rest = m.group(1), m.group(2).strip("_")
            s = f"{rest}-{num}" if rest else f"sp-{num}"
    return s


def speaker_to_persname(raw: str) -> str:
    """'Colin.' → 'Colin',  'La Jeu.' → 'La Jeu'"""
    return raw.strip().rstrip(".").strip()


def speaker_to_who(raw: str) -> str:
    """'Colin.' → '#colin.'"""
    return "#" + raw.strip().lower()


def collect_speakers(tree) -> list:
    """Return sorted list of (xml_id, display_name) for all unique <speaker> values."""
    seen: dict = {}
    for sp in tree.findall(f".//{Q('sp')}"):
        sel = sp.find(Q("speaker"))
        if sel is None:
            continue
        raw = get_text(sel)
        if not raw:
            continue
        xid = speaker_to_xml_id(raw)
        if xid not in seen:
            seen[xid] = speaker_to_persname(raw)
    return sorted(seen.items())


# ── Publication year ───────────────────────────────────────────────────────────

def extract_pub_year(tree) -> str:
    """Extract the original publication year from sourceDesc/biblFull/publicationStmt/date."""
    el = tree.find(
        f".//{Q('sourceDesc')}/{Q('biblFull')}/{Q('publicationStmt')}/{Q('date')}"
    )
    if el is None:
        el = tree.find(f".//{Q('sourceDesc')}//{Q('date')}")
    text = get_text(el)
    m = re.search(r"\b(\d{4})\b", text)
    return m.group(1) if m else "unknown"


# ── Header data extraction ─────────────────────────────────────────────────────

def extract_header_data(tree) -> dict:
    """Pull all needed data from the source teiHeader before any mutation."""
    file_desc  = tree.find(f"{Q('teiHeader')}/{Q('fileDesc')}")
    title_stmt = file_desc.find(Q("titleStmt"))

    titles = []
    for t in title_stmt.findall(Q("title")):
        ttype = t.get("type", "")
        ttext = get_text(t)
        if ttype and ttext:
            titles.append({"type": ttype, "text": ttext})

    author_els = title_stmt.findall(Q("author"))

    surname = ""
    if author_els:
        sn_el = author_els[0].find(f".//{Q('surname')}")
        if sn_el is not None:
            surname = get_text(sn_el)
        if not surname:
            surname = get_text(author_els[0]).split(",")[0].strip()

    title_main = next((t["text"] for t in titles if t["type"] == "main"), "")

    ecco_pub = file_desc.find(Q("publicationStmt"))

    src_desc = file_desc.find(Q("sourceDesc"))
    bib_full = src_desc.find(Q("biblFull")) if src_desc is not None else None

    bib_name = bib_author = bib_publisher = bib_date = bib_pubplace = ""
    bib_notes: list = []

    if bib_full is not None:
        t245 = bib_full.find(f".//{Q('title')}[@type='245']")
        if t245 is None:
            t245 = bib_full.find(f".//{Q('title')}")
        bib_name = get_text(t245)

        auth_el = bib_full.find(f"{Q('titleStmt')}/{Q('author')}")
        if auth_el is None:
            auth_el = bib_full.find(f".//{Q('author')}")
        bib_author = get_text(auth_el)

        bpub = bib_full.find(Q("publicationStmt"))
        if bpub is not None:
            bib_publisher = get_text(bpub.find(Q("publisher")))
            bib_date      = get_text(bpub.find(Q("date")))
            bib_pubplace  = get_text(bpub.find(Q("pubPlace")))

        ns_el = bib_full.find(Q("notesStmt"))
        if ns_el is not None:
            bib_notes = [
                get_text(n) for n in ns_el.findall(Q("note")) if get_text(n)
            ]

    return {
        "titles":        titles,
        "author_els":    author_els,
        "surname":       surname,
        "title_main":    title_main,
        "ecco_pub":      ecco_pub,
        "bib_name":      bib_name,
        "bib_author":    bib_author,
        "bib_publisher": bib_publisher,
        "bib_date":      bib_date,
        "bib_pubplace":  bib_pubplace,
        "bib_notes":     bib_notes,
    }


# ── Dramatis Personae helpers ──────────────────────────────────────────────────

def is_actor_name(text: str) -> bool:
    """True if text looks like an actor attribution (starts with Mr/Mrs/Miss/Mons)."""
    return bool(re.match(r'\s*(Mr|Mrs|Miss|Mons)[\s.]', text.strip(), re.I))


def split_role_desc(text: str) -> tuple:
    """
    Split 'Role — Description' at em/en-dash.
    Returns (role, desc) or (text, '') when no separator found.
    Strips trailing punctuation from the role.
    """
    text = text.strip().rstrip(".,")
    for sep in (" \u2014 ", "\u2014", " \u2013 ", "\u2013", " - "):
        if sep in text:
            parts = text.split(sep, 1)
            return parts[0].strip().rstrip(".,"), parts[1].strip()
    return text.strip().rstrip(".,"), ""


# ── Sex inference from DP section ─────────────────────────────────────────────

def build_dp_sex_map(tree) -> dict:
    """
    Parse the DP section (div1/div2 before rename_divs mutates the tree) and
    return a {xml_id: 'MALE'/'FEMALE'} mapping derived from Men/Women list heads.
    """
    sex_map: dict = {}

    for dp in (
        tree.findall(f".//{Q('div1')}[@type='dramatispersonae']") +
        tree.findall(f".//{Q('div2')}[@type='dramatispersonae']")
    ):
        for lst in dp.findall(Q("list")):
            head_el = lst.find(Q("head"))
            if head_el is None:
                continue
            ht = get_text(head_el).lower()
            if re.search(r'\bmen\b|\bgentlemen\b', ht):
                sex = "MALE"
            elif re.search(r'\bwomen\b|\bladies\b', ht):
                sex = "FEMALE"
            else:
                continue

            for cname in _char_names_from_list(lst):
                xid = speaker_to_xml_id(cname)
                if xid:
                    sex_map[xid] = sex

    return sex_map


def _char_names_from_list(lst) -> list:
    """Extract character name strings from a DP list element (all patterns)."""
    chars = []
    children = list(lst)
    i = 0
    while i < len(children):
        child = children[i]
        local = etree.QName(child.tag).localname

        if local == "label":
            label_text = get_text(child).strip()
            # Advance to next item/label/head
            ni = i + 1
            while ni < len(children) and etree.QName(children[ni].tag).localname not in ("item", "label", "head"):
                ni += 1

            if ni < len(children) and etree.QName(children[ni].tag).localname == "item":
                nested = children[ni].find(Q("list"))
                if nested is not None:
                    chars.extend(_char_names_from_list(nested))
                elif is_actor_name(label_text):
                    # Pattern 1: item = character description
                    char_name, _ = split_role_desc(get_text(children[ni]).strip())
                    if char_name:
                        chars.append(char_name)
                else:
                    # Pattern 3: label = character name
                    char_name, _ = split_role_desc(label_text)
                    if char_name:
                        chars.append(char_name)
                i = ni + 1
            else:
                i += 1

        elif local == "item":
            inner_label = child.find(Q("label"))
            if inner_label is not None:
                # Pattern 2: inner label = character name; split at comma
                char_full = get_text(inner_label).strip()
                char_name = char_full.split(",")[0].strip().rstrip(".")
                if char_name:
                    chars.append(char_name)
            i += 1
        else:
            i += 1

    return chars


def infer_sex_from_map(xml_id: str, sex_map: dict) -> str:
    """
    Look up sex for a speaker xml_id.
    Falls back to prefix matching for abbreviations (e.g. 'alp' → 'alpiew' → FEMALE).
    Returns 'UNKNOWN' when ambiguous or not found.
    """
    if xml_id in sex_map:
        return sex_map[xml_id]
    male_hit   = any(k.startswith(xml_id) for k, v in sex_map.items() if v == "MALE")
    female_hit = any(k.startswith(xml_id) for k, v in sex_map.items() if v == "FEMALE")
    if male_hit and not female_hit:
        return "MALE"
    if female_hit and not male_hit:
        return "FEMALE"
    return "UNKNOWN"


# ── New header builder ─────────────────────────────────────────────────────────

def build_new_header(data: dict, speakers: list, sex_map: dict):
    """Construct a fresh <teiHeader> compliant with the DraCor TEI format."""
    hdr = etree.Element(Q("teiHeader"))

    # ── fileDesc ──────────────────────────────────────────────────────────────
    fd = etree.SubElement(hdr, Q("fileDesc"))

    # titleStmt: titles + author(s)
    ts = etree.SubElement(fd, Q("titleStmt"))
    for t in data["titles"]:
        tel = etree.SubElement(ts, Q("title"))
        tel.set("type", t["type"])
        tel.text = t["text"]
    for auel in data["author_els"]:
        ts.append(copy.deepcopy(auel))

    # publicationStmt — static DraCor block
    ps  = etree.SubElement(fd, Q("publicationStmt"))
    pub = etree.SubElement(ps, Q("publisher"))
    pub.set(QX("id"), "dracor")
    pub.text = "DraCor"
    idno = etree.SubElement(ps, Q("idno"))
    idno.set("type", "URL")
    idno.text = "https://dracor.org"
    av  = etree.SubElement(ps, Q("availability"))
    lic = etree.SubElement(av, Q("licence"))
    ab  = etree.SubElement(lic, Q("ab"))
    ab.text = "CC BY 4.0"
    ref = etree.SubElement(lic, Q("ref"))
    ref.set("target", "https://creativecommons.org/licenses/by/4.0/deed.en")
    ref.text = "Licence"

    # sourceDesc
    sd = etree.SubElement(fd, Q("sourceDesc"))

    # bibl[@type="digitalSource"]
    bibl = etree.SubElement(sd, Q("bibl"))
    bibl.set("type", "digitalSource")
    for tag, val in [
        ("name",      data["bib_name"]),
        ("author",    data["bib_author"]),
        ("publisher", data["bib_publisher"]),
        ("date",      data["bib_date"]),
        ("pubPlace",  data["bib_pubplace"]),
    ]:
        if val:
            el = etree.SubElement(bibl, Q(tag))
            el.text = val
    for note_text in data["bib_notes"]:
        nel = etree.SubElement(bibl, Q("note"))
        nel.text = note_text

    # biblFull[@n="printed source"] — wraps the original ECCO publicationStmt
    bf = etree.SubElement(sd, Q("biblFull"))
    bf.set("n", "printed source")
    if data["ecco_pub"] is not None:
        bf.append(copy.deepcopy(data["ecco_pub"]))

    # ── profileDesc ───────────────────────────────────────────────────────────
    pd   = etree.SubElement(hdr, Q("profileDesc"))
    part = etree.SubElement(pd, Q("particDesc"))
    lp   = etree.SubElement(part, Q("listPerson"))
    for xid, pname in speakers:
        person = etree.SubElement(lp, Q("person"))
        person.set(QX("id"), xid)
        pn = etree.SubElement(person, Q("persName"))
        pn.text = pname
        sex_el = etree.SubElement(person, Q("sex"))
        sex_el.set("value", infer_sex_from_map(xid, sex_map))

    # ── revisionDesc ──────────────────────────────────────────────────────────
    rd = etree.SubElement(hdr, Q("revisionDesc"))
    c1 = etree.SubElement(rd, Q("change"))
    c1.set("when", "2024")
    c1.text = (
        "(JJ) Transformation into valid TEI P5, improving markup, "
        "filling gaps, proofreading, and expanding header."
    )
    c2 = etree.SubElement(rd, Q("change"))
    c2.set("when", "2026")
    c2.text = "(LG) dracorisation"

    return hdr


# ── Body transformations ───────────────────────────────────────────────────────

def rename_divs(root) -> None:
    """Rename div1 / div2 / div3 → div (all attributes preserved)."""
    for local in ("div1", "div2", "div3"):
        for el in root.findall(f".//{Q(local)}"):
            el.tag = Q("div")


# ── castItem helpers ───────────────────────────────────────────────────────────

def make_cast_item(role: str = "", role_desc: str = "", actor: str = "") -> etree.Element:
    """Build a <castItem> with optional <role>, <roleDesc>, <actor> children."""
    actor     = actor.strip().rstrip(".,") if actor else ""
    role      = role.strip()
    role_desc = role_desc.strip()
    ci = etree.Element(Q("castItem"))
    if role:
        r = etree.SubElement(ci, Q("role"))
        r.text = role
    if role_desc:
        rd = etree.SubElement(ci, Q("roleDesc"))
        rd.text = role_desc
    if actor:
        a = etree.SubElement(ci, Q("actor"))
        a.text = actor
    return ci


def convert_list_to_cast_items(lst) -> list:
    """
    Convert a source <list> element to a list of <castItem> elements,
    pairing label/item entries according to source DP pattern:

      Pattern 1 – label = actor (Mr./Mrs.), item = character
      Pattern 2 – item contains inner <label> (character) + tail text (actor)
      Pattern 3 – label = character (no Mr./Mrs. prefix), item = actor
    """
    result = []
    children = list(lst)
    i = 0
    while i < len(children):
        child = children[i]
        local = etree.QName(child.tag).localname

        # ── <head> ────────────────────────────────────────────────────────────
        if local == "head":
            text = get_text(child)
            if text:
                ci = etree.Element(Q("castItem"))
                ci.text = text
                result.append(ci)
            i += 1

        # ── <label> ───────────────────────────────────────────────────────────
        elif local == "label":
            label_text = get_text(child).strip()

            # Find the next sibling that is a structural element
            ni = i + 1
            while ni < len(children) and etree.QName(children[ni].tag).localname not in ("item", "label", "head"):
                ni += 1

            if ni < len(children) and etree.QName(children[ni].tag).localname == "item":
                next_item   = children[ni]
                nested_list = next_item.find(Q("list"))

                if nested_list is not None:
                    # Group header + nested sub-list (e.g. "Sons of Cato")
                    if label_text:
                        ci = etree.Element(Q("castItem"))
                        ci.text = label_text.rstrip(".,").strip()
                        result.append(ci)
                    result.extend(convert_list_to_cast_items(nested_list))

                elif is_actor_name(label_text):
                    # Pattern 1: label = actor, item = character description
                    item_text = get_text(next_item).strip()
                    if item_text:           # skip blank actor-only items
                        role, role_desc = split_role_desc(item_text)
                        result.append(make_cast_item(
                            role=role, role_desc=role_desc, actor=label_text
                        ))

                else:
                    # Pattern 3: label = character, item = actor (or unusual description)
                    role, role_desc = split_role_desc(label_text)
                    actor_text = get_text(next_item).strip()
                    result.append(make_cast_item(
                        role=role, role_desc=role_desc, actor=actor_text
                    ))

                i = ni + 1

            else:
                # Standalone label (no following item)
                if label_text:
                    ci = etree.Element(Q("castItem"))
                    ci.text = label_text.rstrip(".,").strip()
                    result.append(ci)
                i += 1

        # ── <item> ────────────────────────────────────────────────────────────
        elif local == "item":
            inner_label = child.find(Q("label"))
            nested_list = child.find(Q("list"))

            if inner_label is not None:
                # Pattern 2: item contains <label> (character) + tail text (actor)
                char_full  = get_text(inner_label).strip()
                actor_text = (inner_label.tail or "").strip()
                role, role_desc = split_role_desc(char_full)
                result.append(make_cast_item(
                    role=role, role_desc=role_desc, actor=actor_text
                ))

            elif nested_list is not None:
                # Nested list inside a standalone <item>
                result.extend(convert_list_to_cast_items(nested_list))

            else:
                # Plain standalone item (group descriptions, etc.)
                text = get_text(child).strip()
                if text:
                    ci = etree.Element(Q("castItem"))
                    ci.text = text
                    result.append(ci)
            i += 1

        else:
            i += 1

    return result


def convert_dramatis_personae(root) -> None:
    """Replace list-based dramatis personae divs with properly structured <castList>."""
    for dp in root.findall(f".//{Q('div')}[@type='dramatispersonae']"):
        dp.set("type", "Dramatis_Personae")

        cast_list = etree.Element(Q("castList"))

        # Move the existing <head> from the div into castList
        existing_head = dp.find(Q("head"))
        if existing_head is not None:
            dp.remove(existing_head)
            cast_list.append(existing_head)
        else:
            head_el = etree.SubElement(cast_list, Q("head"))
            head_el.text = "Dramatis Personae"

        for lst in dp.findall(Q("list")):
            for ci in convert_list_to_cast_items(lst):
                cast_list.append(ci)

        for lst in dp.findall(Q("list")):
            dp.remove(lst)
        dp.append(cast_list)


def add_who_attributes(root) -> None:
    """Add @who='#{lowercase speaker}' to every <sp> that has a <speaker> child."""
    for sp in root.findall(f".//{Q('sp')}"):
        sel = sp.find(Q("speaker"))
        if sel is not None:
            raw = get_text(sel)
            if raw:
                sp.set("who", speaker_to_who(raw))


# ── standOff ──────────────────────────────────────────────────────────────────

def build_stand_off(year: str):
    """Build the <standOff> element with the print event."""
    so = etree.Element(Q("standOff"))
    le = etree.SubElement(so, Q("listEvent"))
    ev = etree.SubElement(le, Q("event"))
    ev.set("type", "print")
    ev.set("when", year)
    etree.SubElement(ev, Q("desc"))
    return so


# ── Main processing ────────────────────────────────────────────────────────────

def process_file(src_path: str) -> tuple:
    """Process one source file; return (output_filename, xml_string)."""
    parser = etree.XMLParser(remove_comments=False, resolve_entities=False)
    tree   = etree.parse(src_path, parser)
    root   = tree.getroot()

    # 1. Read all data before mutating the tree
    data     = extract_header_data(tree)
    speakers = collect_speakers(tree)
    sex_map  = build_dp_sex_map(tree)   # must run before rename_divs
    pub_year = extract_pub_year(tree)

    # 2. Body transformations
    rename_divs(root)
    convert_dramatis_personae(root)
    add_who_attributes(root)

    # 3. Replace the teiHeader
    new_hdr = build_new_header(data, speakers, sex_map)
    old_hdr = root.find(Q("teiHeader"))
    idx     = list(root).index(old_hdr)
    root.remove(old_hdr)
    root.insert(idx, new_hdr)

    # 4. Set xml:id on root <TEI>
    root.set(QX("id"), "placeholder-id")

    # 5. Insert <standOff> immediately after <teiHeader>
    hdr_idx = list(root).index(new_hdr)
    root.insert(hdr_idx + 1, build_stand_off(pub_year))

    # 6. Generate output filename
    surname    = data["surname"] or "anon"
    title_main = data["title_main"] or "untitled"
    out_name   = f"{slugify(surname)}-{slugify(title_main)}.xml"

    # 7. Indent and serialise (root element only, to skip any source PIs)
    etree.indent(root, space=" ")
    xml_str = etree.tostring(root, encoding="unicode", xml_declaration=False)
    full    = f'<?xml version="1.0" encoding="utf-8"?>\n{PI_LINE}\n{xml_str}\n'

    return out_name, full


def main():
    os.makedirs(TEI_DIR, exist_ok=True)

    unfixable = set(os.listdir(UNFIXABLE)) if os.path.isdir(UNFIXABLE) else set()
    sources   = sorted(glob.glob(os.path.join(XML_DIR, "*.xml")))
    sources   = [f for f in sources if os.path.basename(f) not in unfixable]

    seen:     dict = {}
    success:  int  = 0
    failures: list = []

    for src in sources:
        try:
            out_name, content = process_file(src)

            # Resolve filename collisions by appending -2, -3, …
            if out_name in seen:
                base, ext = out_name.rsplit(".", 1)
                counter = 2
                while f"{base}-{counter}.{ext}" in seen:
                    counter += 1
                out_name = f"{base}-{counter}.{ext}"
                print(
                    f"  NOTE: renamed to {out_name} "
                    f"(collision with {os.path.basename(seen[base + '.' + ext])})"
                )
            seen[out_name] = src

            out_path = os.path.join(TEI_DIR, out_name)
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(content)

            print(f"  OK  {os.path.basename(src):30s} -> {out_name}")
            success += 1

        except Exception:
            print(f"  FAIL {os.path.basename(src)}")
            traceback.print_exc()
            failures.append(src)

    print(f"\n{success}/{len(sources)} files converted successfully.")
    if failures:
        print(f"\n{len(failures)} failure(s):")
        for f in failures:
            print(f"  {os.path.basename(f)}")


if __name__ == "__main__":
    main()
