import 'dart:ui';

import 'package:flutter/material.dart';

import '../theme/nefron_colors.dart';
import '../theme/nefron_spacing.dart';

/// Container translúcido (glassmorphism) — base visual de quase toda a UI.
///
/// Aplica blur no fundo, um preenchimento translúcido e uma borda sutil que,
/// no tema escuro, define a profundidade melhor que sombra. Use APENAS para
/// containers com conteúdo curto/estruturado; texto de leitura longa deve ir
/// em superfície sólida (`context.colors.card`).
class GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final BorderRadius borderRadius;
  final VoidCallback? onTap;

  const GlassCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(Gap.lg),
    this.borderRadius = Radii.rLg,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    // Respeita acessibilidade: se o usuário reduziu transparência/animações,
    // caímos para uma superfície sólida (fallback garante contraste).
    final reduceTransparency = MediaQuery.maybeOf(context)?.disableAnimations ?? false;

    final content = Container(
      decoration: BoxDecoration(
        color: reduceTransparency ? c.card : c.glass,
        borderRadius: borderRadius,
        border: Border.all(color: c.glassStroke, width: Glass.strokeWidth),
      ),
      padding: padding,
      child: child,
    );

    final card = ClipRRect(
      borderRadius: borderRadius,
      child: reduceTransparency
          ? content
          : BackdropFilter(
              filter: ImageFilter.blur(
                  sigmaX: Glass.blurSigma, sigmaY: Glass.blurSigma),
              child: content,
            ),
    );

    if (onTap == null) return card;
    return Material(
      color: Colors.transparent,
      borderRadius: borderRadius,
      child: InkWell(
        borderRadius: borderRadius,
        onTap: onTap,
        child: card,
      ),
    );
  }
}
