def _extract_dots_vectorial(page):
    """
    Détection robuste des points noirs GutMAP.
    Patch critique: on détecte la grille (lignes verticales) pour déduire
    table_x_start/table_x_end + col_width, au lieu d'utiliser des %.
    """
    dots = []

    page_width = page.width

    # ---------------------------
    # 1) Détecter les colonnes via les lignes verticales (grid)
    # ---------------------------
    vlines_x = []
    lines = getattr(page, "lines", None) or []
    for ln in lines:
        x0 = ln.get("x0", None)
        x1 = ln.get("x1", None)
        top = ln.get("top", None)
        bottom = ln.get("bottom", None)
        if None in (x0, x1, top, bottom):
            continue

        # vertical line
        if abs(x0 - x1) < 0.5:
            height = abs(bottom - top)
            # on veut des lignes assez longues (grille tableau)
            if height > 80 and x0 > page_width * 0.40:
                vlines_x.append((x0 + x1) / 2.0)

    # regrouper / dédoublonner par "bucket" (0.8pt)
    vlines_x.sort()
    grid = []
    for x in vlines_x:
        if not grid or abs(x - grid[-1]) > 0.8:
            grid.append(x)

    # on cherche typiquement 8 lignes pour 7 colonnes (ou plus, selon PDF)
    # on prend le bloc "le plus régulier" (espacement proche)
    grid_cols = None
    if len(grid) >= 8:
        best = None
        for i in range(0, len(grid) - 7):
            chunk = grid[i:i+8]
            gaps = [chunk[j+1] - chunk[j] for j in range(7)]
            # régularité: écart-type faible
            if min(gaps) <= 0:
                continue
            mean_gap = sum(gaps) / len(gaps)
            if mean_gap < 8 or mean_gap > 35:
                continue
            var = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
            score = var  # plus petit = mieux
            if best is None or score < best[0]:
                best = (score, chunk)
        if best:
            grid_cols = best[1]

    # fallback (si grille non détectée)
    if grid_cols:
        table_x_start = grid_cols[0]
        table_x_end = grid_cols[-1]
        # bornes internes des colonnes (8 lignes => 7 intervalles)
        boundaries = grid_cols[:]  # 8 valeurs croissantes
        use_grid = True
    else:
        table_x_start = page_width * 0.30
        table_x_end = page_width * 0.80
        table_width = table_x_end - table_x_start
        col_width = table_width / 7
        boundaries = None
        use_grid = False

    def _abundance_from_x(x):
        if not (table_x_start < x < table_x_end):
            return None

        if use_grid and boundaries:
            # trouver dans quel intervalle [b[i], b[i+1]] tombe x
            col_index = None
            for i in range(len(boundaries) - 1):
                if boundaries[i] <= x <= boundaries[i+1]:
                    col_index = i
                    break
            if col_index is None:
                return None
            # col_index 0..6 => abundance -3..+3
            return col_index - 3

        # fallback %
        relative_x = x - table_x_start
        col_index = int(relative_x / col_width)
        col_index = max(0, min(6, col_index))
        return col_index - 3

    def _add_dot_bbox(x0, x1, top, bottom):
        x = (x0 + x1) / 2.0
        y = (top + bottom) / 2.0
        abundance_level = _abundance_from_x(x)
        if abundance_level is None:
            return
        dots.append({"y": y, "x": x, "abundance_level": abundance_level})

    # ---------------------------
    # 2) Collecter dots: curves + rects (+ circles si jamais)
    # ---------------------------
    # CURVES
    curves = getattr(page, "curves", None) or []
    for c in curves:
        x0 = c.get("x0", c.get("x", None))
        x1 = c.get("x1", None)
        top = c.get("top", c.get("y", None))
        bottom = c.get("bottom", None)

        if x1 is None or bottom is None:
            w = c.get("width", None)
            h = c.get("height", None)
            if None in (x0, top, w, h):
                continue
            x1 = x0 + w
            bottom = top + h

        w = abs(x1 - x0)
        h = abs(bottom - top)
        if not (3 < w < 14 and 3 < h < 14):
            continue

        _add_dot_bbox(x0, x1, top, bottom)

    # CIRCLES (souvent vide chez toi, mais on laisse)
    circles = getattr(page, "circles", None) or []
    for c in circles:
        x0 = c.get("x0", None)
        x1 = c.get("x1", None)
        top = c.get("top", None)
        bottom = c.get("bottom", None)
        if None in (x0, x1, top, bottom):
            cx = c.get("x", None)
            cy = c.get("y", None)
            r = c.get("r", None)
            if None in (cx, cy, r):
                continue
            x0, x1 = cx - r, cx + r
            top, bottom = cy - r, cy + r

        w = abs(x1 - x0)
        h = abs(bottom - top)
        if not (3 < w < 14 and 3 < h < 14):
            continue

        _add_dot_bbox(x0, x1, top, bottom)

    # RECTS
    rects = getattr(page, "rects", None) or []
    for r in rects:
        x0 = r.get("x0", None)
        x1 = r.get("x1", None)
        top = r.get("top", None)
        bottom = r.get("bottom", None)
        if None in (x0, x1, top, bottom):
            continue

        w = abs(x1 - x0)
        h = abs(bottom - top)
        if not (3 < w < 14 and 3 < h < 14):
            continue

        _add_dot_bbox(x0, x1, top, bottom)

    # ---------------------------
    # 3) Trier + dédoublonner (même logique)
    # ---------------------------
    dots.sort(key=lambda d: d["y"])

    unique = []
    last_y = None
    for d in dots:
        if last_y is None or abs(d["y"] - last_y) > 5:
            unique.append(d)
            last_y = d["y"]

    return unique
