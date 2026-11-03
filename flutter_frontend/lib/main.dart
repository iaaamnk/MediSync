import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'screens/patient_portal_screen.dart';
import 'screens/doctor_portal_screen.dart';
import 'models/report_model.dart';

void main() {
  runApp(const MediSyncApp());
}

class MediSyncApp extends StatelessWidget {
  const MediSyncApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MediSync Hospital Dashboard',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0D9488),
          primary: const Color(0xFF0D9488),
          secondary: const Color(0xFF3B82F6),
          background: const Color(0xFFF8FAFC),
        ),
        textTheme: GoogleFonts.plusJakartaSansTextTheme(Theme.of(context).textTheme),
        scaffoldBackgroundColor: const Color(0xFFF8FAFC),
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.white,
          foregroundColor: Color(0xFF0F172A),
          elevation: 1,
        ),
      ),
      home: const DashboardShell(),
    );
  }
}

class DashboardShell extends StatefulWidget {
  const DashboardShell({Key? key}) : super(key: key);

  @override
  State<DashboardShell> createState() => _DashboardShellState();
}

class _DashboardShellState extends State<DashboardShell> {
  int _currentPortalIndex = 0; // 0 = Patient, 1 = Doctor
  MedicalReport? _sharedReport;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [Color(0xFF0D9488), Color(0xFF3B82F6)]),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Text("⚕️", style: TextStyle(fontSize: 18)),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Text("MediSync", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                Text("Hospital AI Health System", style: TextStyle(fontSize: 11, color: Color(0xFF0D9488))),
              ],
            ),
          ],
        ),
        actions: [
          // Portal Switcher Segment
          SegmentedButton<int>(
            segments: const [
              ButtonSegment<int>(value: 0, label: Text("Patient"), icon: Icon(Icons.person, size: 16)),
              ButtonSegment<int>(value: 1, label: Text("Doctor"), icon: Icon(Icons.medical_services, size: 16)),
            ],
            selected: {_currentPortalIndex},
            onSelectionChanged: (Set<int> newSelection) {
              setState(() {
                _currentPortalIndex = newSelection.first;
              });
            },
            style: const ButtonStyle(
              visualDensity: VisualDensity.compact,
            ),
          ),
          const SizedBox(width: 12),
        ],
      ),
      body: _currentPortalIndex == 0
          ? PatientPortalScreen(
              onReportLoaded: (report) {
                setState(() => _sharedReport = report);
              },
            )
          : DoctorPortalScreen(initialReport: _sharedReport),
    );
  }
}

