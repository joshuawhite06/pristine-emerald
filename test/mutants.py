#!/usr/bin/env python3
"""Mutation tests for the PID code: plant known bugs, one at a time, and check
that test_personality catches each. Run after changing src/personality_tools.c
or SetBoxMonPersonalityPreservingData:

    python3 test/mutants.py            # all mutants (~40 s each)
    python3 test/mutants.py no_gender_check

Each mutant is a list of exact (old, new) replacements; the source is restored
afterwards, and the test build is rebuilt from the real source at the end.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

MUTANTS = {
 'unown_wrong_bits': ('src/personality_tools.c', [
    ('            u32 b3 = ((trainerXor >> 8) ^ b1) & 3;\n', '            u32 b3 = (trainerXor ^ b1) & 3;\n')]),
 'no_wurmple_check': ('src/personality_tools.c', [
    ('    if (t->species == SPECIES_WURMPLE\n     && ((personality >> 16) % 10 <= 4) != ((t->oldPersonality >> 16) % 10 <= 4))\n        return FALSE;\n    return TRUE;\n}\n\n// The full rules', '    return TRUE;\n}\n\n// The full rules'),
    ('    if (t->species == SPECIES_WURMPLE\n     && ((personality >> 16) % 10 <= 4) != ((t->oldPersonality >> 16) % 10 <= 4))\n        return FALSE;\n    if (t->species == SPECIES_UNOWN', '    if (t->species == SPECIES_UNOWN')]),
 'no_unown_check': ('src/personality_tools.c', [
    ('    if (t->species == SPECIES_UNOWN)\n    {\n        u32 raw = UNOWN_RAW(personality);\n        if (!(t->unownRawOk[raw / 8] & (1 << (raw % 8))))\n            return FALSE;\n    }\n', ''),
    ('    if (t->species == SPECIES_UNOWN\n     && GET_UNOWN_LETTER(personality) != GET_UNOWN_LETTER(t->oldPersonality))\n        return FALSE;\n', '')]),

 'no_reorder_no_verify': ('src/pokemon.c', [
    ('    for (i = 0; i < 4; i++)\n        *GetSubstruct(boxMon, personality, i) = substructs[i];\n', ''),
    ('    if (!ok)\n    {\n        *boxMon = backup;\n        return FALSE;\n    }\n    return TRUE;', '    return TRUE;')]),
 'no_gender_check': ('src/personality_tools.c', [
    ('        if ((t->genderRatio > (personality & 0xFF)) != t->oldIsFemale)\n            return FALSE;\n', ''),
    ('    if (GetGenderFromSpeciesAndPersonality(t->species, personality)\n     != GetGenderFromSpeciesAndPersonality(t->species, t->oldPersonality))\n        return FALSE;\n', '')]),
 'no_stat_recalc': ('src/personality_tools.c', [
    ('    if (result != PERSONALITY_CHANGE_FAILED)\n        CalculateMonStats(mon);\n', '')]),
 'no_rollback_on_bad_checksum': ('src/pokemon.c', [
    ('    boxMon->checksum = CalculateBoxMonChecksum(boxMon);\n    EncryptBoxMon(boxMon);\n', '    boxMon->checksum = CalculateBoxMonChecksum(boxMon) + 1;\n    EncryptBoxMon(boxMon);\n'),
    ('    if (!ok)\n    {\n        *boxMon = backup;\n        return FALSE;\n    }\n    return TRUE;', '    return TRUE;')]),
}

def main(names):
    missed = []
    try:
        for name in names or list(MUTANTS):
            path, edits = MUTANTS[name]
            p = REPO / path
            original = p.read_text()
            mutated = original
            for old, new in edits:
                assert mutated.count(old) == 1, f"{name}: pattern not found once in {path}: {old!r}"
                mutated = mutated.replace(old, new)
            p.write_text(mutated)
            try:
                build = subprocess.run(["scripts/build.sh", "PRISTINE_TEST=1"], cwd=REPO, capture_output=True, text=True)
                if build.returncode:
                    print(f"{name}: build failed")
                    missed.append(name)
                    continue
                run = subprocess.run([sys.executable, "-m", "unittest", "test.cases.test_personality"],
                                     cwd=REPO, capture_output=True, text=True)
                summary = [l for l in run.stderr.splitlines() if l.startswith(("Ran", "OK", "FAILED"))]
                print(f"{name}: {'caught' if run.returncode else 'MISSED'} {summary}")
                if not run.returncode:
                    missed.append(name)
            finally:
                p.write_text(original)
    finally:
        subprocess.run(["scripts/build.sh", "PRISTINE_TEST=1"], cwd=REPO, capture_output=True)
    if missed:
        print(f"not caught: {missed}")
        return 1
    print("all mutants caught")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
