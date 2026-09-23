"""Which transmission a machine has — Phase 255.

Phase 254 wrote twelve rows about scooter CVTs and gave them a `make`
column naming seven marques. Two of those marques also build motorcycles,
so a Gold Wing, a CBR1000RR, a Grom, an R1 and an XS650 were each handed
seven or eight rows about variator rollers and drive belts. Nothing was
wrong with the rows. What was missing was any way to ask *what the machine
in front of us actually has*.

This module answers that, and the shape of the answer is the point.

**It returns a candidate set, not a value.** `make/model/year` genuinely
cannot separate a manual Africa Twin from a DCT Africa Twin — Honda sells
both in the same model year — so a resolver that returned one value would
have to invent it. This one says `{manual, dct}` and lets the caller
decide what is safe to show.

**Unknown is all six.** A machine nobody can classify has every
transmission as a candidate, and `applicability.row_applies` includes a
scoped row only when its declared set covers every candidate. So an
unknown machine receives scoped rows only from a row that declares all
six, which is the same as being unscoped. That is the fail-closed policy,
and it is what fixes the 254 defect: **the Gold Wing is fixed by the
absence of an entry, not by the presence of one.** The lookup below exists
to *preserve* retrieval for the machines that should keep it.

**Nothing here reads row text.** No keyword matching, in seed or at
runtime. Machines are classified by an explicit, sourced table; rows are
classified by an explicit declaration in the seed file. The two never meet
through a regex.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping, Optional

from motodiag.core.models import VehicleTransmission

logger = logging.getLogger(__name__)

#: Every value. What an unknown machine's candidate set is, and therefore
#: the fail-closed baseline.
ALL_TRANSMISSIONS: frozenset[str] = frozenset(v.value for v in VehicleTransmission)

#: How a resolution was reached. Returned alongside the candidates so the
#: withheld-rows counter can attribute the cost of the policy instead of
#: reporting one undifferentiated number.
Provenance = Literal[
    "explicit",            # the vehicle row carried a transmission
    "model-sourced",       # a lookup entry, sourced to a manufacturer document
    "powertrain-default",  # electric with no gearbox, and no override
    "ambiguous",           # the model is sold with more than one transmission
    "unknown",             # nothing classified it — all six candidates
]


@dataclass(frozen=True)
class TransmissionEntry:
    """One machine, classified from a document that says so.

    `aliases` is an explicit list of spellings, and it is explicit for a
    reason Phase 255 had to learn twice. A name search does not prove
    absence: "SMAX returns zero corpus rows" and "XC155 returns two" can
    be one machine wearing two names, and this resolver must not conclude
    anything from one spelling. Nothing is derived — no fuzzy matching, no
    splitting `PCX150` into `PCX` and `150`. If a spelling occurs in the
    wild, it is written down here.

    `source` names the document the classification came from and quotes
    the sentence that carries it. A row with no document does not exist in
    this corpus, and neither does an entry here.
    """

    make: str
    canonical: str
    transmission: VehicleTransmission
    aliases: tuple[str, ...]
    source: str
    #: What produced this entry's source stage (Phase 257), as model@effort:
    #: "subconscious/glm-5.3-marathon@default", or the fallback while
    #: Subconscious is unavailable — "claude-opus-5-5@medium" (and one entry
    #: from its first cut, "claude-sonnet-5@default"). None for entries not
    #: sourced by a batch. A field, not prose, so the fallback's entries can
    #: be selected and re-run mechanically.
    source_route: Optional[str] = None


@dataclass(frozen=True)
class Resolution:
    """What the resolver concluded, and how."""

    candidates: frozenset[str]
    provenance: Provenance
    entry: Optional[TransmissionEntry] = None

    @property
    def certain(self) -> bool:
        """True when exactly one transmission is possible."""
        return len(self.candidates) == 1

    @property
    def value(self) -> Optional[str]:
        """The single value, or None when the answer is a set."""
        return next(iter(self.candidates)) if self.certain else None


def _norm(text: Any) -> str:
    """Lower-case, punctuation to spaces, runs collapsed.

    Deliberately shallow. It makes `PCX-150`, `PCX 150` and `pcx  150` the
    same string and stops there: `PCX150` is a *different* string and gets
    its own alias, because splitting letters from digits is the fuzzy
    matching this resolver does not do.
    """
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def _tokens(text: Any) -> tuple[str, ...]:
    return tuple(_norm(text).split())


CVT = VehicleTransmission.CVT
MANUAL = VehicleTransmission.MANUAL
SEMI_CENT = VehicleTransmission.SEMI_AUTO_CENTRIFUGAL

_E = TransmissionEntry

#: Machines classified from a manufacturer document read first-hand.
#:
#: Read what this table is *for*. It is not an attempt to classify the
#: world's motorcycles — that is a later phase with its own workflow and
#: refuter, sourced from manufacturer specification pages. Every machine
#: absent from it resolves to unknown and loses scoped rows, which is the
#: correct outcome for a Gold Wing and the accepted cost for a Ruckus.
#:
#: **There is no make-default.** Not even for marques that build nothing
#: but scooters. A make-default has to be right for every machine the
#: marque ever sold, and Piaggio's hand-shift Vespa PX and the Genuine
#: Stella are the standing counter-examples — neither is sourced here, and
#: a default would be the only thing speaking for them. Marque-wide
#: inference is exactly the bulk guessing this phase forbids.
TRANSMISSION_LOOKUP: tuple[TransmissionEntry, ...] = (
    # --- Honda -----------------------------------------------------------
    # Honda states it, under Honda's own trade name. Phase 255 searched for
    # "belt", "drive belt", "weight roller", "CVT" and "transmission" and
    # concluded these manuals said nothing -- the exact error Phase 254's row
    # 4604 exists to warn about, made one phase later. The word is
    # **V-matic**, and the specification tables print it with a RATIO RANGE,
    # which is what settles it: a fixed primary reduction is one number.
    _E("Honda", "PCX", CVT, ("pcx", "pcx 125", "pcx125", "pcx 150", "pcx150",
                             "pcx 160", "pcx160", "pcx150a"),
       "Honda PCX125 owner's manual 2021 and 2025 PCX owner's manual: "
       "'the Honda Genuine Parts for drive system such as the drive belt "
       "and weight rollers'; both carry a 'V-BELT indicator'. Weight "
       "rollers are variator-specific — a final-drive belt has none."),
    _E("Honda", "Ruckus", CVT, ("ruckus", "nps50", "nps 50", "honda ruckus"),
       "Honda Ruckus owner's manuals 31GGA6300 (2012), 31GGA720 (2022), "
       "31GJP600 (2024) and 31GJP610 (2025), Specifications table: "
       "'Primary reduction  V-matic (2.85:1 ~ 0.86:1)'. A ratio RANGE is a "
       "continuously variable drive; a fixed primary reduction prints one "
       "number, as the same tables do for 'Final reduction 13.708'."),
    _E("Honda", "Metropolitan", CVT, ("metropolitan", "chf50", "chf 50",
                                      "honda metropolitan"),
       "Honda Metropolitan owner's manuals 31GJB640 (2020) through 31GJB690 "
       "(2026): 'Primary reduction  V-matic (2.85:1 - 0.86:1)'. Corroborated "
       "by the CHF50 SERVICE manual, whose specification table carries the "
       "full variator set -- 'Drive belt width', 'Movable drive face', "
       "'Driven pulley', 'Weight roller', 'Clutch outer I.D.', 'Lining "
       "thickness' -- and a chapter titled 'KICKSTARTER/DRIVE PULLEY/DRIVEN "
       "PULLEY/CLUTCH'."),
    _E("Honda", "SH125i/SH150i", CVT, ("sh125i", "sh150i", "sh 125i", "sh 150i",
                                       "sh125", "sh150"),
       "Honda SH125i/SH150i 21YM owner's manual 32K0RA00 / 00X32-K0R-A000: "
       "'the drive belt and weight rollers, to ensure correct Torque "
       "Control operation', plus a 'Drive Belt' maintenance row."),
    _E("Honda", "Super Cub C125", SEMI_CENT, ("c125", "super cub c125", "super cub"),
       "Honda parts catalogue 13K0GK01 (© Honda Motor Co., Ltd. 2018): "
       "'WEIGHT SET, PRIMARY CLUTCH' 22535-K73-T30 in group E-7, friction "
       "plates in E-8, and owner's manual 32K0GC20 showing a gear-position "
       "indicator with no clutch lever."),
    _E("Honda", "CT125 Hunter Cub", SEMI_CENT, ("ct125", "ct 125", "trail 125",
                                                "ct125a", "hunter cub"),
       "Honda parts catalogue 13K2EB0AJ 'CT125 HUNTER CUB' (© Honda Motor "
       "Co., Ltd. 2020): the same three groups as the C125 — 'WEIGHT SET, "
       "PRIMARY CLUTCH' in E-7 'ONE WAY CLUTCH', 'DISK, CLUTCH FRICTION' "
       "in E-8, 'LEVER COMP., CLUTCH' in E-6."),
    # Phase 257 tranche 1, run Honda_20260922_233404, both refute verdicts
    # kept. The plan expected the GROM125 service manual's page images to
    # carry this entry, because its text layer is OCR; the batch found a
    # strictly better source first — Honda's own spec pages, digital
    # text. The OCR corroborates and is deliberately not the citation.
    _E("Honda", "Grom 125", MANUAL,
       ("grom", "grom 125", "grom125", "grom abs", "grom sp",
        "grom (msx125s)", "grom abs (msx125as)", "grom sp (msx125ss)",
        "msx125", "msx 125", "msx125s", "msx125as", "msx125ss"),
       "Honda's own Grom specifications pages: 2025 (Model 'Grom ABS "
       "(MSX125AS) / Grom SP (MSX125SS) / Grom (MSX125S)') reads "
       "'Transmission  Manual; 5 speeds' and 'Clutch  Multiplate wet'; the "
       "2020 page for the 124.9 cc Grom reads 'Transmission  Manual; four "
       "speeds'. The GROM125 service manual's OCR page 9 says the same "
       "(constant-mesh four-speed, wet multiplate clutch, 1-N-2-3-4) but "
       "is OCR evidence and is not the citation.",
       source_route="subconscious/glm-5.3-marathon@default"),

    # --- Yamaha ----------------------------------------------------------
    _E("Yamaha", "Zuma 125", CVT, ("zuma 125", "zuma125", "yw125", "yw125y"),
       "Yamaha Zuma 125 service manual 32SF819770E0, cover 'Model : "
       "YW125Y': 'Transmission type V-belt automatic'. The cover is also "
       "where the model-code alias comes from."),
    _E("Yamaha", "Zuma 50", CVT, ("zuma 50", "zuma50", "zuma 50f", "zuma50f",
                                  "yw50", "yw50t", "yw50fb", "yw50fk",
                                  "yw50fxe"),
       "A separate machine from the 125 and sourced separately: Yamaha "
       "owner's manuals 5PJ-F8199-13 (YW50T), 1CD-F8199-10 (YW50FB), "
       "1CD-F8199-17 (YW50FK) and 2DT-F8199-10 (YW50FXE) each schedule "
       "'V-belt' as a maintenance item alongside 'Final transmission oil'. "
       "The model-code aliases come from those covers."),
    _E("Yamaha", "XC155 / SMAX", CVT, ("xc155", "xc 155", "xc155f", "xc 155f",
                                       "smax", "s max", "s-max"),
       "Two NHTSA campaigns, Yamaha's own defect-notice text. The NAME: "
       "16V892000 reads 'recalling certain model year 2015 XC155F SMAX "
       "scooters', and campaign 20V277000 lists both XC155 and XC155F for "
       "MY2015 — so XC155 = XC155F = SMAX, in the manufacturer's words. The "
       "TRANSMISSION: 21V251000 reads 'The primary sheave nut may loosen and "
       "fall off'; a primary sheave is the CVT drive pulley. NOTE 'SMAX' "
       "occurs exactly ONCE in NHTSA's entire post-2010 flat recall file "
       "(245,336 rows), which is why Phase 255 searched for it, found "
       "nothing, and wrongly concluded the equivalence was unsourced."),
    _E("Yamaha", "XMAX", CVT,
       ("xmax", "xmax 125", "xmax125", "yp125ra",
        "xmax 250", "xmax250", "czd250", "czd250 a", "czd250a",
        "czd250d", "czd250d a",
        "xmax 300", "xmax300", "czd300", "czd300 a", "czd300a",
        "czd300d", "czd300d a",
        "xmax tech max", "xmax 300 tech max", "xmax 250 tech max"),
       "Yamaha owner's manuals 2DM-F819D-P3 ('YP125RA XMAX'), BMK-F8199-F0 "
       "('CZD250-A (XMAX 250)', 'CZD300-A (XMAX 300)') and PBMKF8199SAS "
       "('CZD250D-A (XMAX 250 TECH MAX)', 'CZD300D-A (XMAX 300 TECH MAX)'): "
       "each carries a 'TRIP V-BELT' belt-replacement counter. One entry "
       "for the family because all three documents agree and the junction "
       "carries the bare form 'XMAX'. These covers are ALSO the evidence "
       "that XC155 is not an XMAX: Yamaha's XMAX codes are YP125RA, CZD250 "
       "and CZD300, and none of them is XC155 — which is correct, and incomplete: XC155 is the SMAX, sourced in its own entry above."),

    # --- Suzuki ----------------------------------------------------------
    # Phase 257, run Suzuki_20260923_093052: Suzuki's
    # own current spec pages, fetched by acquire.py into
    # ~/research/motodiag/acquired/Suzuki/ with script-written provenance;
    # every refute verdict kept, every page names its model (model scope).
    # The SV650 is deliberately absent: its page is the SV650 ABS, which
    # refute read as family evidence (bug fix #3).
    # E12 correction (2026-09-23): GSX-R750, GSX-R1000, GSX-R600, GSX-S1000,
    # Boulevard M109R and V-Strom 1050 were reverted to unknown — their pages
    # name only a gear count, a slipper/assist clutch or a quick-shifter, none
    # of which shows a rider-operated clutch or a foot-shift pattern.
    _E("Suzuki", "V-Strom 650", MANUAL, ("v strom 650", "vstrom 650", "vstrom650"),
       "suzukicycles.com/adventure/2025/v-strom-650 (2025 V-Strom 650): 'The "
       "multi-plate clutch has precise push rod actuation of the pressure "
       "plate for a light lever pull and a consistent release point.' — the "
       "rider's clutch pull. Re-quoted twice under E12: first from a gear "
       "count ('The six-speed transmission suits…'), then from an Easy Start "
       "sentence that names the clutch lever only in a negation ('without "
       "pulling in the clutch lever'), which E12 no longer accepts.",
       source_route="subconscious/glm-5.3-marathon@default"),
    # Live vehicle #8 is a 2019 SV650. Run Suzuki_20260923_141812 on the
    # fallback source route (claude-opus-5-5 at medium; Subconscious
    # suspended), refute on Opus: kept, names_model true — the same
    # document, quote and classification as the first cut's claude-sonnet-5
    # run (Suzuki_20260923_123652). From the ABS edition's page — the
    # operator's one named exception.
    _E("Suzuki", "SV650", MANUAL, ("sv650", "sv 650", "sv650 abs", "sv 650 abs"),
       "From the ABS edition's page (the base model's only current page): "
       "suzukicycles.com/street/2026/sv650-abs (2026 SV650 ABS): 'The "
       "multi-plate clutch has precise push rod actuation of the pressure "
       "plate for a light pull and consistent release point.' — the rider's "
       "clutch pull.",
       source_route="claude-opus-5-5@medium"),
    _E("Suzuki", "DR-Z400S", MANUAL, ("dr z400s", "drz400s", "dr z 400s", "drz 400s"),
       "suzukicycles.com/dualsport/2024/dr-z400s (2024 DR-Z400S): 'Compact, "
       "five-speed transmission utilizes a cable-operated clutch with a "
       "separate magnesium outer cover for simplified clutch maintenance.'",
       source_route="subconscious/glm-5.3-marathon@default"),
    _E("Suzuki", "Boulevard C50", MANUAL, ("boulevard c50", "boulevard c 50"),
       "suzukicycles.com/cruiser/2025/boulevard-c50 (2025 Suzuki Boulevard "
       "C50): 'With a light pull, the clutch feeds engine power to the "
       "smooth-shifting five-speed transmission and out to the clean shaft "
       "drive.'",
       source_route="subconscious/glm-5.3-marathon@default"),

    # --- Kawasaki --------------------------------------------------------
    # Phase 257, run Kawasaki_20260923_100438: Kawasaki's own model-year
    # spec pages, fetched by acquire.py (cookie jar) into
    # ~/research/motodiag/acquired/Kawasaki/; each quote is the page's own
    # spec row and names a foot-shift pattern ("return shift") or a manual
    # clutch; refute kept each with names_model true. Three come from the
    # ABS edition's page — the operator's one named exception — and say so.
    _E("Kawasaki", "Ninja ZX-10R", MANUAL, ("zx 10r", "zx10r", "ninja zx 10r", "ninja zx10r"),
       "kawasaki.com/en-us/motorcycle/ninja/supersport/ninja-zx-10r/2026-ninja-zx-10r "
       "(2026 Ninja ZX-10R), spec table: 'Transmission 6-speed, return shift'.",
       source_route="subconscious/glm-5.3-marathon@default"),
    _E("Kawasaki", "Ninja ZX-6R", MANUAL, ("zx 6r", "zx6r", "ninja zx 6r", "ninja zx6r"),
       "kawasaki.com/en-us/motorcycle/ninja/supersport/ninja-zx-6r/2027-ninja-zx-6r "
       "(2027 Ninja ZX-6R), spec table: 'Transmission 6-speed, return shift'.",
       source_route="subconscious/glm-5.3-marathon@default"),
    _E("Kawasaki", "Ninja H2", MANUAL, ("ninja h2", "ninjah2", "ninja h2 abs"),
       "From the ABS edition's page (the base model's only current page): "
       "kawasaki.com/en-us/motorcycle/ninja/hypersport/ninja-h2/2026-ninja-h2-abs "
       "(2026 Ninja H2 ABS), spec table: 'Transmission 6-speed, return shift, "
       "dog-ring'.",
       source_route="subconscious/glm-5.3-marathon@default"),
    _E("Kawasaki", "KLR650", MANUAL, ("klr650", "klr 650"),
       "kawasaki.com/en-us/motorcycle/klr/dual-sport/klr650/2026-klr650 (2026 "
       "KLR650), spec table: 'Transmission 5-speed, return shift with wet "
       "multi-disc manual clutch'.",
       source_route="subconscious/glm-5.3-marathon@default"),
    _E("Kawasaki", "Z900", MANUAL, ("z900", "z 900", "z900 abs"),
       "From the ABS edition's page (the base model's only current page): "
       "kawasaki.com/en-us/motorcycle/z/supernaked/z900/2026-z900-abs (2026 Z900 "
       "ABS), spec table: 'Transmission 6-speed, return shift'.",
       source_route="subconscious/glm-5.3-marathon@default"),
    _E("Kawasaki", "Ninja 300", MANUAL, ("ninja 300", "ninja300", "ninja 300 abs"),
       "From the ABS edition's page (the base model's only current page): "
       "kawasaki.com/en-us/motorcycle/ninja/sport/ninja-300/2026-ninja-300-abs "
       "(2026 Ninja 300 ABS), spec table: 'Transmission 6-speed, return shift'.",
       source_route="subconscious/glm-5.3-marathon@default"),
    _E("Kawasaki", "KLX300", MANUAL, ("klx300", "klx 300"),
       "kawasaki.com/en-us/motorcycle/klx/dual-sport/klx300/2026-klx300 (2026 "
       "KLX300), spec table: 'Transmission 6-speed, return shift with wet "
       "multi-disc manual clutch'.",
       source_route="subconscious/glm-5.3-marathon@default"),
    _E("Kawasaki", "Z650", MANUAL, ("z650", "z 650"),
       "kawasaki.com/en-us/motorcycle/z/supernaked/z650/2025-z650 (2025 Z650), "
       "spec table: 'Transmission 6-speed, return shift'.",
       source_route="subconscious/glm-5.3-marathon@default"),

    # --- Kymco -----------------------------------------------------------
    _E("Kymco", "Agility", CVT, ("agility", "agility 50", "agility50",
                                 "agility 125", "agility125"),
       "Kymco Agility 50/125 owner's manual: "
       "'Transmission ... Automatic CVT'."),
    _E("Kymco", "People S", CVT, ("people s", "peoples", "people s 50",
                                  "people s 125", "people s 200", "people",
                                  "people s 250", "people 250"),
       "Kymco People S 50/125/200 owner's manual: "
       "'Transmission ... Automatic CVT'."),
    _E("Kymco", "Super 8", CVT, ("super 8", "super8", "super 8 50r", "super8 50r"),
       "Kymco Super 8 50R owner's manual: a 'CVT FILTER' maintenance row "
       "and 'DRIVE BELT ... Inspect every 5000km, replace every 20000km'."),
    _E("Kymco", "Like 150i", CVT, ("like 150i", "like150i", "like"),
       "Kymco Like 150i owner's manual: a 'CVT FILTER' row and "
       "'* DRIVE BELT Inspect every 5000km,replace every 20000km'. Phase "
       "254 recorded that this PDF's internal Title metadata reads "
       "'DOWNTOWN 125i(ok)' — High confidence in the quotes, Medium that "
       "the document is authored as a Like 150i manual."),
    # Phase 257 tranche 1, run Kymco_20260922_232607, refute verdict kept.
    # The manual is a scanned PDF, so refute rendered the spec page itself
    # (pypdfium2, PDF page 57, printed 56, landscape) and read the line from
    # the image — the OCR layer was never the evidence.
    _E("Kymco", "K-Pipe", MANUAL,
       ("k-pipe", "k-pipe 125", "kpipe", "kpipe 125", "kpipe125",
        "t300-kb25ka-a"),
       "Kymco K-Pipe 125 owner's manual (Version T300-KB25KA-A), spec table: "
       "'Transmission.......................... 4-speed, foot shift'. "
       "Corroborated by a rider clutch cable with 5-10 mm free play and an "
       "N-1-2-3-4 gear pattern diagram.",
       source_route="subconscious/glm-5.3-marathon@default"),

    # --- SYM -------------------------------------------------------------
    # SYM is the marque that proves the table is not 'scooter maker means
    # CVT': the same maker's Symba is a Cub and its Wolf is a motorcycle.
    _E("SYM", "Symba 100", SEMI_CENT, ("symba", "symba 100", "symba100"),
       "SYM Symba owner's manual: 'Clutch  Wet multi-plate type, auto "
       "centrifugal clutch' and 'Transmission  4 - speed gear change'. "
       "This is the mechanism definition of semi_auto_centrifugal, in the "
       "maker's own words."),
    # The Classic 150 is the Wolf 150 wearing its spec-page name: the same
    # owner's manual (page 6 'MODEL: WOLF SERIES', 149.5 cc) has its spec
    # table headed 'Model Classic 150' (PA15C1-A / PA15C1-C). Phase 257
    # tranche 1, run SYM_20260922_232240, refute verdict kept.
    _E("SYM", "Wolf 150", MANUAL, ("wolf", "wolf 150", "wolf150",
                                  "wolf classic 150", "wolfclassic150",
                                  "wolf classic", "wolf series"),
       "SYM Wolf 150 owner's manual: 'Squeeze the clutch lever fully, "
       "operate change pedal to the proper position, then release the "
       "clutch lever to make a gear change.' (TRANSMISSION OPERATION, PDF "
       "page 18; spec table PDF page 35: 'Clutch Wet disk type / "
       "Transmission Gear', five speeds). Earlier evidence: 'Clutch "
       "lever' in the controls list and a 'Clutch lever free play' "
       "maintenance item."),
    # Phase 257 tranche 1, run SYM_20260922_232240, refute verdict kept.
    _E("SYM", "Wolf CR300i", MANUAL,
       ("wolf cr300i", "wolf cr 300i", "wolfcr300i", "cr300i", "cr 300i",
        "pf30a3 eu"),
       "SYM Wolf CR300i owner's manual (sha256 e50db79f…, the library's "
       "v2/sympdf copy and the tranche's fetch are byte-identical), PDF page "
       "22: 'Start engine, squeeze the clutch lever fully, push shift pedal "
       "down to engage the 1st gear'. Re-quoted under E12 (2026-09-23): the "
       "first quote, 'Always use the clutch when changing gear.' (page 12), "
       "names no clutch lever or shift pedal. Spec table PDF page 24: 'Model "
       "WOLF CR 300i / Specification PF30A3-EU', 278 cc.",
       source_route="subconscious/glm-5.3-marathon@default"),
    _E("SYM", "Mio 50", CVT, ("mio", "mio 50", "mio50"),
       "SYM Mio 50 owner's manual: 'Clutch  Centrifugal type  "
       "Transmission  CVT'."),
    _E("SYM", "Jet 4 RX125", CVT, ("jet 4", "jet4", "jet 4 rx125", "jet4 rx125",
                                   "jet 4 125", "jet 4 rx 125"),
       "SYM Jet 4 RX125 owner's manual: 'Clutch  Centrifugal type  "
       "Transmission  CVT'."),
    _E("SYM", "Jet 50/100", CVT, ("jet 50", "jet50", "jet 100", "jet100",
                                  "jet euro 50", "jet euro 100"),
       "SYM service manual 7326249: 'the technical data of each component "
       "inspection and repair for the SANYANG JET 50/100 and JET Euro "
       "50/100 series motorcycle', specification table 'Primary Reduction "
       "BELT ... Secondary Reduction GEAR'. A BELT primary reduction is the "
       "variator. NOTE this is a DIFFERENT machine from the Jet 4 RX125 "
       "above, which is why the bare alias 'jet' belongs to neither."),
    _E("SYM", "Joyride", CVT, ("joyride", "joyride 125", "joyride 150",
                               "joyride 200", "joyride 200 efi", "rv200"),
       "SYM service manual 7429958: 'the technical data ... for the Sanyang "
       "JOYRIDE 125/150/200 motorcycle', chapter 8 titled 'V-BELT DRIVING "
       "SYSTEM/FOOT STARTER'. Corroborated by the RV200 owner's manual "
       "specification table, 'Model Joyride 200 EFi / Joyride 125'."),
    _E("SYM", "ADX125", CVT, ("adx", "adx125", "adx 125"),
       "SYM ADX125 owner's manual: 'Transmission  CVT'."),
    _E("SYM", "Fiddle III", CVT, ("fiddle", "fiddle iii", "fiddle 3", "fiddle3"),
       "SYM Fiddle III owner's manual: a combined 'Drive belt/roller  I R' "
       "maintenance row. Belt and roller together are variator-specific."),
    _E("SYM", "Symphony ST", CVT, ("symphony", "symphony st"),
       "SYM Symphony ST owner's manual: a combined 'Drive belt/roller  "
       "I R' maintenance row."),
    _E("SYM", "Symply 125", CVT, ("symply", "symply 125", "symply125"),
       "SYM Symply service manual: chapter 8 'V-BELT DRIVING SYSTEM/KICK "
       "STARTER ARM', and maintenance rows 'CVT driving device (belt)' and "
       "'CVT driving device (roller)'."),

    # --- Piaggio and Vespa ------------------------------------------------
    # Piaggio prints one house sentence across its service manuals, which
    # is the single best transmission statement in the whole set.
    _E("Vespa", "LX 50", CVT, ("lx 50", "lx50"),
       "Piaggio service station manual 633416 (Vespa LX 50): 'Transmission "
       "With automatic expandable pulley variator, torque server, V-belt, "
       "automatic clutch, gear reduction unit.'"),
    _E("Vespa", "LX 125/150", CVT, ("lx", "lx 125", "lx125", "lx 150", "lx150"),
       "Piaggio service station manual 633976 (Vespa LX 125 - 150 4T Euro "
       "3): 'Automatic transmission', and a fault table entry 'Inefficient "
       "automatic transmission — Check the rollers and the pulley "
       "movement'."),
    _E("Vespa", "S 50", CVT, ("s 50", "s50", "vespa s 50"),
       "Piaggio service station manual 664787-664795 'Vespa S 50 2T': "
       "'Transmission  Automatic expandable pulley variator...'."),
    _E("Vespa", "Primavera 150", CVT, ("primavera", "primavera 150",
                                       "primavera s 150", "primavera s",
                                       "sprint", "sprint s", "sprint 125",
                                       "sprint 150", "sprint s 125",
                                       "sprint s 150"),
       "Vespa Primavera/S 150 owner's manual: 'The vehicle is fitted with "
       "direct drive automatic transmission.' Its cover reads 'Vespa "
       "Primavera S - Sprint S 125-150 Ed. 01_05/2018 Cod. 1Q000662', which "
       "is the source for the Sprint aliases — Phase 255 dropped them as "
       "unsourced without reading the cover. NOTE the vocabulary trap — "
       "Piaggio's 'direct drive' here means no intermediate gearbox, NOT "
       "this axis's `direct_drive` value. The same manual contains zero "
       "occurrences of 'variator'."),
    _E("Vespa", "GTS 300/310", CVT, ("gts", "gts 300", "gts300", "gts 310",
                                     "gts310", "gts 300 super", "gts super 300",
                                     "gts 300 i", "gts 300 ie", "gts 310 hpe"),
       "Vespa GTS owner's manual (cover 'Gts 310 HPE'): 'the vehicle is "
       "equipped with automatic transmission' and 'THE AUTOMATIC "
       "TRANSMISSION MAKES THE REAR WHEEL TURN EVEN WHEN THE THROTTLE IS "
       "SLIGHTLY TWISTED'. The 'GTS Super 300' spelling is sourced "
       "separately, to the Piaggio workshop manual whose cover reads "
       "'GTS Super 300 ie (2008)'."),
    _E("Piaggio", "Typhoon 50", CVT, ("typhoon", "typhoon 50", "typhoon50"),
       "Piaggio Typhoon 50 service station manual: 'Transmission With "
       "automatic expandable pulley variator, torque server, V-belt, "
       "automatic clutch, gear reduction unit.'"),
    _E("Piaggio", "Fly", CVT, ("fly", "fly 125", "fly125", "fly 150",
                               "fly150", "fly 50", "fly50"),
       "Two books, one per displacement, so the 50 is not inferred from the "
       "125: Piaggio service station manual (Fly 125 - 150 4T) -- "
       "'Transmission  With automatic expandable pulley variator with torque "
       "server, V belt, automatic clutch, gear reduction unit'; and workshop "
       "manual 633212 'MSS Fly 50 4T' -- 'Transmission  With automatic "
       "expandable pulley...'."),
    _E("Piaggio", "Beverly", CVT, ("beverly", "beverly 125", "beverly125",
                                   "beverly tourer 125", "beverly tourer"),
       "Piaggio Beverly 125 service station manual: 'Main drive  Automatic "
       "expandable pulley variator with torque server, V-belt, automatic "
       "self-ventilating clutch'. The Tourer 125 spelling is sourced "
       "separately, to service station manual 665018 (EN) 'Beverly Tourer "
       "125'. The Beverly 250 is NOT covered by either book and gets no "
       "alias."),
    _E("Piaggio", "MP3 400", CVT, ("mp3", "mp3 400", "mp3 400 i e", "mp3 250",
                                   "mp3 500"),
       "Piaggio service station manual 664503(EN) (MP3 400 i.e.): "
       "'TRANSMISSION  Automatic expandable pulley variator with torque "
       "server, V-belt, automatic clutch.'"),

    # --- Genuine ---------------------------------------------------------
    # Genuine prints the same spec row in every book: 'Transmission Type
    # Continuously Variable (CVT)  Clutch  Dry, Centrifugal'.
    _E("Genuine", "Buddy 50", CVT, ("buddy 50", "buddy50"),
       "Genuine Buddy 50 owner's manual MY2027: 'Transmission Type "
       "Continuously Variable (CVT)  Clutch  Dry, Centrifugal'."),
    _E("Genuine", "Buddy 125", CVT, ("buddy", "buddy 125", "buddy125"),
       "Genuine Buddy 125 owner's manual: 'Transmission Type Continuously "
       "Variable (CVT)  Clutch  Dry, Centrifugal'."),
    _E("Genuine", "Buddy 170i", CVT, ("buddy 170", "buddy170", "buddy 170i",
                                      "buddy170i"),
       "Genuine Buddy 170 owner's manual 2023: 'Transmission Type "
       "Continuously Variable (CVT)  Clutch  Dry, Centrifugal', plus "
       "'V Belt * Check variator rollers, sliders, etc for wear'."),
    _E("Genuine", "Buddy Kick 125", CVT, ("buddy kick", "buddy kick 125",
                                          "buddykick", "buddykick 125"),
       "Genuine Buddy Kick 125 owner's manual: 'Dry centrifugal govern "
       "weight  V-belt  C.V.T', plus a 'CVT Filter' maintenance row."),
    _E("Genuine", "Bella Classic 50", CVT, ("bella", "bella classic",
                                            "bella classic 50", "bella 50"),
       "Genuine Bella Classic 50 owner's manual: 'Transmission Type "
       "Continuously Variable (CVT)', and a 'Transmission Variator / "
       "Clutch*' service row reading 'Check rollers, sliders, clutch "
       "pads'."),
    _E("Genuine", "Brio 50i", CVT, ("brio", "brio 50", "brio50", "brio 50i",
                                    "brio50i"),
       "Genuine Brio 50i owner's manual: 'Transmission Type Continuously "
       "Variable (CVT)  Clutch  Dry, Centrifugal'."),
    _E("Genuine", "Hooligan 170i", CVT, ("hooligan", "hooligan 170",
                                         "hooligan170", "hooligan 170i"),
       "Genuine Hooligan 170 owner's manual: 'clutch type DRY TYPE  gear "
       "shift type AUTOMATIC (V BELT)'."),
    _E("Genuine", "Rattler 125", CVT, ("rattler", "rattler 125", "rattler125"),
       "Genuine Rattler 125 owner's manual: 'Your scooter is equipped with "
       "a CVT transmission', and 'Check the transmission for belt and "
       "roller wear'."),
    _E("Genuine", "Rattler 200i", CVT, ("rattler 200", "rattler200",
                                        "rattler 200i", "rattler200i"),
       "Genuine Rattler 200i owner's manual: 'Your scooter is equipped "
       "with a CVT transmission'."),
    _E("Genuine", "Roughhouse 50", CVT, ("roughhouse", "roughhouse 50",
                                         "roughhouse50"),
       "Genuine Roughhouse 50 owner's manual: 'Transmission Type "
       "Continuously Variable (CVT)  Clutch  Dry, Centrifugal'."),
    _E("Genuine", "Urbano 125", CVT, ("urbano", "urbano 125", "urbano125"),
       "Genuine Urbano 125 owner's manual: 'Your scooter is equipped with "
       "a CVT transmission'."),
    _E("Genuine", "Urbano 200i", CVT, ("urbano 200", "urbano200",
                                       "urbano 200i", "urbano200i"),
       "Genuine Urbano 200i owner's manual: 'Your scooter is equipped with "
       "a CVT transmission'."),

    # --- Bintelli --------------------------------------------------------
    # Not a corpus marque, so these entries reach no rows today. They are
    # here because a user may add one tomorrow, and because this manual is
    # the counter-example that shaped Phase 254's belt row.
    _E("Bintelli", "Sprint", CVT, ("sprint", "sprint 49", "sprint 50"),
       "Bintelli User's Manual, 'Technical Specifications': 'Transmission "
       "CVT', belt model 'Gates 669MM'."),
    _E("Bintelli", "Breeze", CVT, ("breeze",),
       "Bintelli User's Manual, 'Technical Specifications': 'Transmission "
       "CVT'."),
    _E("Bintelli", "Edge", CVT, ("edge",),
       "Bintelli User's Manual, 'Technical Specifications': 'Transmission "
       "CVT'."),
    _E("Bintelli", "Scorch", CVT, ("scorch",),
       "Bintelli User's Manual, 'Technical Specifications': 'Transmission "
       "CVT'."),
    _E("Bintelli", "Havoc", CVT, ("havoc",),
       "Bintelli User's Manual, 'Technical Specifications': 'Transmission "
       "CVT', belt model 'Gates 835MM'."),
)

#: Models sold with more than one transmission in the same model year.
#: `make/model/year` cannot separate them and this resolver will not
#: pretend otherwise — it returns the set and lets fail-closed do the rest.
AMBIGUOUS_MODELS: tuple[tuple[str, tuple[str, ...], frozenset[str]], ...] = (
    ("Honda", ("africa twin", "crf1100l", "crf1000l", "crf1100l africa twin"),
     frozenset({MANUAL.value, VehicleTransmission.DCT.value})),
    ("Honda", ("nc750x", "nc750", "nc 750x"),
     frozenset({MANUAL.value, VehicleTransmission.DCT.value})),
    ("Honda", ("gold wing", "goldwing", "gl1800", "gl1800 gold wing",
      "gold wing gl1800", "gl 1800"),
     frozenset({MANUAL.value, VehicleTransmission.DCT.value})),
    ("Honda", ("rebel 1100", "cmx1100"),
     frozenset({MANUAL.value, VehicleTransmission.DCT.value})),
)

#: Electric machines the `electric ⇒ direct_drive` default must NOT touch.
#: The default is a default, not a rule: the Brammo Empulse has a
#: six-speed gearbox, Electric Motion trials machines have a rider clutch
#: and a single ratio that fits none of the six values cleanly, and the
#: Ninja 7 Hybrid is an automated manual. Each resolves to unknown rather
#: than to a value nobody sourced.
POWERTRAIN_DEFAULT_EXCLUDED: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Brammo", ("empulse", "empulse r")),
    ("Victory", ("empulse", "empulse tt")),
    ("Kawasaki", ("ninja 7", "ninja 7 hybrid", "ninja7")),
    ("Electric Motion", ("escape", "epure", "epure race", "epure sport")),
)


def _alias_match(make: str, model: str, aliases: Iterable[str]) -> bool:
    """Whole-token match of `model` against an explicit alias list.

    The make prefix is stripped first, so "Honda PCX150" and "PCX150" are
    the same query. After that the comparison is exact on the normalised
    token sequence. Nothing is split, nothing is scored, and no alias is
    matched as a substring of the query — "Jet" must not match "Jetstream"
    and "Like" must not match "Like a Vespa".
    """
    query = _tokens(model)
    make_tokens = _tokens(make)
    if make_tokens and query[: len(make_tokens)] == make_tokens:
        query = query[len(make_tokens):]
    if not query:
        return False
    return any(query == _tokens(a) for a in aliases)


def resolve_transmission(
    make: str,
    model: str,
    *,
    explicit: Optional[str] = None,
    powertrain: Optional[str] = None,
) -> Resolution:
    """What transmissions this machine might have, and how we know.

    Precedence, in order, and it stops at the first rung that answers:

    1. **explicit** — the vehicle row carries a transmission. A human or a
       future mobile field said so, and nothing here second-guesses it.
    2. **model lookup** — an entry sourced to a manufacturer document.
       Ambiguous models answer here too, with their whole candidate set.
    3. **powertrain default** — `electric` with no gearbox is
       `direct_drive`, minus the machines that prove it is a default and
       not a rule.
    4. **unknown** — all six candidates, which withholds every scoped row.
    """
    if explicit:
        value = _norm(explicit).replace(" ", "_")
        if value in ALL_TRANSMISSIONS:
            return Resolution(frozenset({value}), "explicit")
        logger.warning(
            "transmission: ignoring unrecognised explicit value %r", explicit
        )

    make_n = _norm(make)

    for entry in TRANSMISSION_LOOKUP:
        if _norm(entry.make) != make_n:
            continue
        if _alias_match(entry.make, model, entry.aliases):
            return Resolution(frozenset({entry.transmission.value}),
                              "model-sourced", entry)

    for amb_make, aliases, candidates in AMBIGUOUS_MODELS:
        if _norm(amb_make) == make_n and _alias_match(amb_make, model, aliases):
            return Resolution(candidates, "ambiguous")

    if _norm(powertrain) == "electric":
        for exc_make, aliases in POWERTRAIN_DEFAULT_EXCLUDED:
            if _norm(exc_make) == make_n and _alias_match(exc_make, model, aliases):
                return Resolution(ALL_TRANSMISSIONS, "unknown")
        return Resolution(
            frozenset({VehicleTransmission.DIRECT_DRIVE.value}),
            "powertrain-default",
        )

    return Resolution(ALL_TRANSMISSIONS, "unknown")


# --- Where the cost of the policy is counted ------------------------------
#
# Phase 255 counted withheld rows here, in a module-level dict, behind
# `record_withheld` / `withheld_snapshot` / `reset_withheld`. All three are
# gone.
#
# They could not work. Every CLI command is a fresh process, so the
# aggregate was zero by the time anyone could read it, and Phase 209B's
# orphan guard caught the two accessors and recorded them with the note
# "retire these or wire that route; do not let the entry sit."
#
# Phase 256 wired the route: `knowledge/retrieval.py` writes each
# withholding to the `retrieval_withheld` table (migration 064) and
# `withheld_report` reads it back, surfaced as `motodiag kb withheld`.
# That table is the lookup's to-do list -- every machine that lost rows,
# ordered by what the missing entry costs.
