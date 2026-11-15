import 'package:flutter/material.dart';
import '../models/report_model.dart';
import '../services/api_service.dart';

class DoctorPortalScreen extends StatefulWidget {
  final MedicalReport? initialReport;

  const DoctorPortalScreen({Key? key, this.initialReport}) : super(key: key);

  @override
  State<DoctorPortalScreen> createState() => _DoctorPortalScreenState();
}

class _DoctorPortalScreenState extends State<DoctorPortalScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _tokenCtrl = TextEditingController();
  final _docNameCtrl = TextEditingController(text: "Dr. Sarah Jenkins, MD");
  final _notesCtrl = TextEditingController();

  MedicalReport? _patientReport;
  bool _isLoading = false;
  List<Appointment> _doctorAppointments = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    if (widget.initialReport != null) {
      _patientReport = widget.initialReport;
      _tokenCtrl.text = widget.initialReport!.token;
    }
    _loadAppointments();
  }

  Future<void> _loadAppointments() async {
    final appts = await ApiService.getAppointments();
    setState(() {
      _doctorAppointments = appts;
    });
  }

  Future<void> _fetchReport() async {
    final token = _tokenCtrl.text.trim();
    if (token.isEmpty) return;

    setState(() => _isLoading = true);
    final report = await ApiService.getReportByToken(token);
    setState(() {
      _isLoading = false;
      _patientReport = report;
    });

    if (report == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("No report found with this token"), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _saveNotes() async {
    if (_patientReport == null || _notesCtrl.text.trim().isEmpty) return;

    final success = await ApiService.addDoctorNotes(
      _patientReport!.id,
      _docNameCtrl.text,
      _notesCtrl.text.trim(),
    );

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Doctor consultation note attached successfully!"), backgroundColor: Colors.teal),
      );
      _notesCtrl.clear();
      // Re-fetch report to see updated notes
      _fetchReport();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          color: Colors.white,
          child: TabBar(
            controller: _tabController,
            labelColor: const Color(0xFF0F766E),
            unselectedLabelColor: Colors.grey.shade600,
            indicatorColor: const Color(0xFF0F766E),
            indicatorWeight: 3,
            tabs: const [
              Tab(icon: Icon(Icons.qr_code_scanner), text: "Scan & Clinical Chart"),
              Tab(icon: Icon(Icons.event_note), text: "Consultations Queue"),
            ],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildChartTab(),
              _buildQueueTab(),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildChartTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Token / QR Scan Card
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            elevation: 1,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Patient QR Code / Token Lookup", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 6),
                  const Text("Enter or scan the patient's report access token to view clinical indicators:", style: TextStyle(fontSize: 12, color: Colors.black54)),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _tokenCtrl,
                          decoration: const InputDecoration(
                            hintText: "e.g. TK-AB12CD",
                            border: OutlineInputBorder(),
                            contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF0F766E),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        onPressed: _fetchReport,
                        icon: const Icon(Icons.search, size: 18),
                        label: const Text("Access"),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          if (_isLoading)
            const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator(color: Color(0xFF0F766E)))),

          if (!_isLoading && _patientReport != null) ...[
            // Patient details & parameters
            Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              elevation: 1,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(_patientReport!.patientName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(color: const Color(0xFFCCFBF1), borderRadius: BorderRadius.circular(6)),
                          child: Text(_patientReport!.token, style: const TextStyle(fontWeight: FontWeight.bold, fontFamily: 'monospace', color: Color(0xFF0F766E))),
                        ),
                      ],
                    ),
                    Text("Report: ${_patientReport!.reportTitle}", style: const TextStyle(color: Colors.black54, fontSize: 13)),
                    const Divider(height: 24),
                    const Text("Clinical Parameters:", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                    const SizedBox(height: 8),
                    ..._patientReport!.parameters.map((p) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Text(p.name, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                          ),
                          Text("${p.value}  (Ref: ${p.referenceRange})", style: const TextStyle(fontSize: 13)),
                          const SizedBox(width: 8),
                          Text(p.status, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: p.status.toLowerCase().contains("high") ? Colors.red : (p.status.toLowerCase().contains("low") ? Colors.blue : Colors.green))),
                        ],
                      ),
                    )),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Attending Doctor Consultation Notes Form
            Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              elevation: 1,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("✍️ Physician Consultation Notes", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _docNameCtrl,
                      decoration: const InputDecoration(labelText: "Attending Doctor", border: OutlineInputBorder()),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _notesCtrl,
                      maxLines: 3,
                      decoration: const InputDecoration(labelText: "Clinical Observations & Prescriptions", border: OutlineInputBorder()),
                    ),
                    const SizedBox(height: 12),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF0F766E),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      onPressed: _saveNotes,
                      child: const Center(child: Text("Sign & Save Consultation Note", style: TextStyle(fontWeight: FontWeight.bold))),
                    ),
                    const SizedBox(height: 16),
                    const Text("Consultation History:", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    const SizedBox(height: 8),
                    if (_patientReport!.doctorNotes.isEmpty)
                      const Text("No prior consultation notes recorded.", style: TextStyle(fontSize: 12, color: Colors.black54))
                    else
                      ..._patientReport!.doctorNotes.map((n) => Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(color: Colors.grey.shade50, borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.grey.shade200)),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text("🩺 ${n.doctorName}", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                            const SizedBox(height: 4),
                            Text(n.notes, style: const TextStyle(fontSize: 13)),
                          ],
                        ),
                      )),
                  ],
                ),
              ),
            ),
          ]
        ],
      ),
    );
  }

  Widget _buildQueueTab() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _doctorAppointments.length,
      itemBuilder: (context, i) {
        final a = _doctorAppointments[i];
        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(a.patientName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(color: Colors.teal.shade50, borderRadius: BorderRadius.circular(6)),
                      child: Text(a.status, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: Color(0xFF0F766E))),
                    ),
                  ],
                ),
                Text("📅 ${a.date} at ${a.time} • Attending: ${a.doctorName}", style: const TextStyle(fontSize: 12, color: Colors.black54)),
                const SizedBox(height: 4),
                Text("Reason: \"${a.reason}\"", style: const TextStyle(fontSize: 13)),
                if (a.reportToken != null) ...[
                  const SizedBox(height: 6),
                  TextButton.icon(
                    style: TextButton.styleFrom(padding: EdgeInsets.zero),
                    onPressed: () {
                      _tokenCtrl.text = a.reportToken!;
                      _tabController.animateTo(0);
                      _fetchReport();
                    },
                    icon: const Icon(Icons.document_scanner, size: 16, color: Color(0xFF0F766E)),
                    label: Text("Open Attached Report (${a.reportToken})", style: const TextStyle(color: Color(0xFF0F766E), fontSize: 12)),
                  ),
                ]
              ],
            ),
          ),
        );
      },
    );
  }
}

