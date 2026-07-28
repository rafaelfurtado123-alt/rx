import 'package:flutter/material.dart';

/// Tokens de cor do Design System `néfron·`.
///
/// Nunca usar cores cruas na UI — sempre referenciar estes tokens semânticos.
/// Cada token tem variante para tema claro e escuro. As cores clínicas
/// (ok/warn/critical) acompanham SEMPRE ícone + rótulo (nunca cor isolada),
/// para acessibilidade e daltonismo.
class NefronColors extends ThemeExtension<NefronColors> {
  // Marca / acento
  final Color primary;
  final Color primaryContainer;
  final Color secondary;

  // Superfícies (base do glass)
  final Color bgGradientTop;
  final Color bgGradientBottom;
  final Color glass; // preenchimento translúcido do vidro
  final Color glassStroke; // borda do vidro
  final Color card; // superfície sólida (leitura longa)

  // Texto
  final Color textPrimary;
  final Color textSecondary;
  final Color onBrand;

  // Semânticas clínicas
  final Color ok;
  final Color warn;
  final Color critical;
  final Color info;
  final Color clinAnemia;
  final Color clinDmo;
  final Color clinAdequacy;

  const NefronColors({
    required this.primary,
    required this.primaryContainer,
    required this.secondary,
    required this.bgGradientTop,
    required this.bgGradientBottom,
    required this.glass,
    required this.glassStroke,
    required this.card,
    required this.textPrimary,
    required this.textSecondary,
    required this.onBrand,
    required this.ok,
    required this.warn,
    required this.critical,
    required this.info,
    required this.clinAnemia,
    required this.clinDmo,
    required this.clinAdequacy,
  });

  /// Paleta do tema claro.
  static const light = NefronColors(
    primary: Color(0xFF0E7C86),
    primaryContainer: Color(0xFFCFF5F1),
    secondary: Color(0xFF4F6BED),
    bgGradientTop: Color(0xFFEAF3F5),
    bgGradientBottom: Color(0xFFF7FAFB),
    glass: Color(0x8CFFFFFF), // rgba(255,255,255,0.55)
    glassStroke: Color(0xA6FFFFFF),
    card: Color(0xFFFFFFFF),
    textPrimary: Color(0xFF0B1620),
    textSecondary: Color(0xFF48606E),
    onBrand: Color(0xFFFFFFFF),
    ok: Color(0xFF1FA971),
    warn: Color(0xFFE0A500),
    critical: Color(0xFFE5484D),
    info: Color(0xFF4F6BED),
    clinAnemia: Color(0xFFC2410C),
    clinDmo: Color(0xFF7C3AED),
    clinAdequacy: Color(0xFF0E7C86),
  );

  /// Paleta do tema escuro (padrão do produto).
  static const dark = NefronColors(
    primary: Color(0xFF22D3C5),
    primaryContainer: Color(0xFF0B4A50),
    secondary: Color(0xFF8AA0FF),
    bgGradientTop: Color(0xFF0C1620),
    bgGradientBottom: Color(0xFF0A0F14),
    glass: Color(0x8C16202A), // rgba(22,32,42,0.55)
    glassStroke: Color(0x14FFFFFF),
    card: Color(0xFF121A22),
    textPrimary: Color(0xFFEAF2F5),
    textSecondary: Color(0xFF9DB2BE),
    onBrand: Color(0xFF04211F),
    ok: Color(0xFF3BD98C),
    warn: Color(0xFFF0BE3A),
    critical: Color(0xFFFF6369),
    info: Color(0xFF8AA0FF),
    clinAnemia: Color(0xFFFB923C),
    clinDmo: Color(0xFFA78BFA),
    clinAdequacy: Color(0xFF22D3C5),
  );

  /// Cor semântica para um estado clínico ('ok' | 'warn' | 'critical' | 'info').
  Color statusColor(String status) => switch (status) {
        'ok' => ok,
        'warn' => warn,
        'critical' => critical,
        _ => info,
      };

  @override
  NefronColors copyWith({
    Color? primary,
    Color? primaryContainer,
    Color? secondary,
    Color? bgGradientTop,
    Color? bgGradientBottom,
    Color? glass,
    Color? glassStroke,
    Color? card,
    Color? textPrimary,
    Color? textSecondary,
    Color? onBrand,
    Color? ok,
    Color? warn,
    Color? critical,
    Color? info,
    Color? clinAnemia,
    Color? clinDmo,
    Color? clinAdequacy,
  }) {
    return NefronColors(
      primary: primary ?? this.primary,
      primaryContainer: primaryContainer ?? this.primaryContainer,
      secondary: secondary ?? this.secondary,
      bgGradientTop: bgGradientTop ?? this.bgGradientTop,
      bgGradientBottom: bgGradientBottom ?? this.bgGradientBottom,
      glass: glass ?? this.glass,
      glassStroke: glassStroke ?? this.glassStroke,
      card: card ?? this.card,
      textPrimary: textPrimary ?? this.textPrimary,
      textSecondary: textSecondary ?? this.textSecondary,
      onBrand: onBrand ?? this.onBrand,
      ok: ok ?? this.ok,
      warn: warn ?? this.warn,
      critical: critical ?? this.critical,
      info: info ?? this.info,
      clinAnemia: clinAnemia ?? this.clinAnemia,
      clinDmo: clinDmo ?? this.clinDmo,
      clinAdequacy: clinAdequacy ?? this.clinAdequacy,
    );
  }

  @override
  NefronColors lerp(ThemeExtension<NefronColors>? other, double t) {
    if (other is! NefronColors) return this;
    return NefronColors(
      primary: Color.lerp(primary, other.primary, t)!,
      primaryContainer: Color.lerp(primaryContainer, other.primaryContainer, t)!,
      secondary: Color.lerp(secondary, other.secondary, t)!,
      bgGradientTop: Color.lerp(bgGradientTop, other.bgGradientTop, t)!,
      bgGradientBottom: Color.lerp(bgGradientBottom, other.bgGradientBottom, t)!,
      glass: Color.lerp(glass, other.glass, t)!,
      glassStroke: Color.lerp(glassStroke, other.glassStroke, t)!,
      card: Color.lerp(card, other.card, t)!,
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t)!,
      textSecondary: Color.lerp(textSecondary, other.textSecondary, t)!,
      onBrand: Color.lerp(onBrand, other.onBrand, t)!,
      ok: Color.lerp(ok, other.ok, t)!,
      warn: Color.lerp(warn, other.warn, t)!,
      critical: Color.lerp(critical, other.critical, t)!,
      info: Color.lerp(info, other.info, t)!,
      clinAnemia: Color.lerp(clinAnemia, other.clinAnemia, t)!,
      clinDmo: Color.lerp(clinDmo, other.clinDmo, t)!,
      clinAdequacy: Color.lerp(clinAdequacy, other.clinAdequacy, t)!,
    );
  }
}

/// Atalho para acessar os tokens de cor a partir do contexto.
extension NefronColorsX on BuildContext {
  NefronColors get colors => Theme.of(this).extension<NefronColors>()!;
}
