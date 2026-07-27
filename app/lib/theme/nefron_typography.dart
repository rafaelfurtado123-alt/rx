import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Tipografia do Design System `néfron·`.
///
/// Inter para UI; IBM Plex Mono (tabular) para números clínicos — doses,
/// resultados de exames e Kt/V — de modo que colunas numéricas alinhem.
abstract final class NefronType {
  /// Estilos de texto da UI, tintados com [color].
  static TextTheme textTheme(Color color, Color secondary) {
    final base = GoogleFonts.interTextTheme();
    return base.copyWith(
      displaySmall: base.displaySmall?.copyWith(
          fontSize: 32, fontWeight: FontWeight.w700, color: color),
      titleLarge: base.titleLarge?.copyWith(
          fontSize: 22, fontWeight: FontWeight.w600, color: color),
      titleMedium: base.titleMedium?.copyWith(
          fontSize: 18, fontWeight: FontWeight.w600, color: color),
      bodyLarge: base.bodyLarge?.copyWith(fontSize: 15, color: color),
      bodyMedium: base.bodyMedium?.copyWith(fontSize: 15, color: color),
      labelLarge: base.labelLarge?.copyWith(
          fontSize: 13, fontWeight: FontWeight.w500, color: color),
      bodySmall: base.bodySmall?.copyWith(fontSize: 12, color: secondary),
    );
  }

  /// Estilo monoespaçado tabular para números clínicos (doses, exames, Kt/V).
  static TextStyle mono({
    required Color color,
    double size = 15,
    FontWeight weight = FontWeight.w500,
  }) {
    return GoogleFonts.ibmPlexMono(
      fontSize: size,
      fontWeight: weight,
      color: color,
      fontFeatures: const [FontFeature.tabularFigures()],
    );
  }

  /// Número vital grande (peso, PA), monoespaçado.
  static TextStyle vital(Color color) =>
      mono(color: color, size: 32, weight: FontWeight.w700);
}
