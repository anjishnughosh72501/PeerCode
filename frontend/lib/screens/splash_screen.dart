import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key, required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0D0F),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Text(
              'PeerCode',
              style: GoogleFonts.inter(
                  fontSize: 36,
                  fontWeight: FontWeight.w800,
                  color: const Color(0xFF7C84FA)),
            ),
            const SizedBox(height: 8),
            Text(
              'LAN Collaborative Editor',
              style: GoogleFonts.inter(
                  fontSize: 13, color: const Color(0xFF5C5C72)),
            ),
            const SizedBox(height: 40),
            const SizedBox(
              width: 24,
              height: 24,
              child: CircularProgressIndicator(
                  color: Color(0xFF7C84FA), strokeWidth: 2),
            ),
            const SizedBox(height: 20),
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              child: Text(
                status,
                key: ValueKey<String>(status),
                style: GoogleFonts.inter(
                    fontSize: 12, color: const Color(0xFF5C5C72)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
