#pragma once

#include "MatDinHot.h"

using namespace System;
using namespace System::ComponentModel;
using namespace System::Collections;
using namespace System::Windows::Forms;
using namespace System::Data;
using namespace System::Drawing;

namespace DinHotSys {

	/// <summary>
	/// Summary for SistemaControl
	///
	/// WARNING: If you change the name of this class, you will need to change the
	///          'Resource File Name' property for the managed resource compiler tool
	///          associated with all .resx files this class depends on.  Otherwise,
	///          the designers will not be able to interact properly with localized
	///          resources associated with this form.
	/// </summary>
	public ref class SistemaControl : public System::Windows::Forms::Form
	{
	public:	MatDinHot *_masker;
	private: System::Windows::Forms::RadioButton^  rBDelete;



	private:	System::Windows::Forms::Form ^_ventanaPrincipal;
	public:
		SistemaControl(void)
		{
			InitializeComponent();
			//
			//TODO: Add the constructor code here
			//
		}
		SistemaControl(System::Windows::Forms::Form ^vPrincipal)
		{
			_ventanaPrincipal = vPrincipal;
			InitializeComponent();
			//
			//TODO: Add the constructor code here
			//
		}
	protected:
		/// <summary>
		/// Clean up any resources being used.
		/// </summary>
		~SistemaControl()
		{
			if (components)
			{
				delete components;
			}
		}
	private: System::Windows::Forms::MenuStrip^  MenuPrincipal;
	protected: 
	private: System::Windows::Forms::ToolStripMenuItem^  archivoToolStripMenuItem;
	private: System::Windows::Forms::TableLayoutPanel^  tableLayoutPanel1;
	private: System::Windows::Forms::TabControl^  tabControlGraph;
	private: System::Windows::Forms::TabPage^  tabPage0;
	private: System::Windows::Forms::TableLayoutPanel^  tableLayoutPanel2;
	private: System::Windows::Forms::TabPage^  tabPage1;


	private: System::Windows::Forms::TabPage^  tabPage2;


	private: System::Windows::Forms::TabPage^  tabPage3;


	private: System::Windows::Forms::TabPage^  tabPage4;



	private: System::Windows::Forms::Panel^  panelTab0Izq;
	private: System::Windows::Forms::Panel^  panelTab0Der;
	private: System::Windows::Forms::ListView^  listView1;
	private: System::Windows::Forms::ColumnHeader^  columnHeader1;
	private: System::Windows::Forms::ColumnHeader^  columnHeader2;
	private: System::Windows::Forms::WebBrowser^  webBrowser1;
	private: System::Windows::Forms::RadioButton^  rbCreateMove;
	private: System::ComponentModel::BackgroundWorker^  bwControl;































	private:
		/// <summary>
		/// Required designer variable.
		/// </summary>
		System::ComponentModel::Container ^components;

#pragma region Windows Form Designer generated code
		/// <summary>
		/// Required method for Designer support - do not modify
		/// the contents of this method with the code editor.
		/// </summary>
		void InitializeComponent(void)
		{
			System::Windows::Forms::ListViewGroup^  listViewGroup5 = (gcnew System::Windows::Forms::ListViewGroup(L"Modo Operación", System::Windows::Forms::HorizontalAlignment::Left));
			System::Windows::Forms::ListViewGroup^  listViewGroup6 = (gcnew System::Windows::Forms::ListViewGroup(L"Información", System::Windows::Forms::HorizontalAlignment::Left));
			System::Windows::Forms::ListViewItem^  listViewItem5 = (gcnew System::Windows::Forms::ListViewItem(L"OntheFly"));
			System::Windows::Forms::ListViewItem^  listViewItem6 = (gcnew System::Windows::Forms::ListViewItem(L"Confirmación"));
			this->MenuPrincipal = (gcnew System::Windows::Forms::MenuStrip());
			this->archivoToolStripMenuItem = (gcnew System::Windows::Forms::ToolStripMenuItem());
			this->tableLayoutPanel1 = (gcnew System::Windows::Forms::TableLayoutPanel());
			this->tabControlGraph = (gcnew System::Windows::Forms::TabControl());
			this->tabPage0 = (gcnew System::Windows::Forms::TabPage());
			this->tableLayoutPanel2 = (gcnew System::Windows::Forms::TableLayoutPanel());
			this->panelTab0Izq = (gcnew System::Windows::Forms::Panel());
			this->panelTab0Der = (gcnew System::Windows::Forms::Panel());
			this->listView1 = (gcnew System::Windows::Forms::ListView());
			this->columnHeader1 = (gcnew System::Windows::Forms::ColumnHeader());
			this->columnHeader2 = (gcnew System::Windows::Forms::ColumnHeader());
			this->rbCreateMove = (gcnew System::Windows::Forms::RadioButton());
			this->tabPage1 = (gcnew System::Windows::Forms::TabPage());
			this->tabPage2 = (gcnew System::Windows::Forms::TabPage());
			this->tabPage3 = (gcnew System::Windows::Forms::TabPage());
			this->tabPage4 = (gcnew System::Windows::Forms::TabPage());
			this->webBrowser1 = (gcnew System::Windows::Forms::WebBrowser());
			this->bwControl = (gcnew System::ComponentModel::BackgroundWorker());
			this->rBDelete = (gcnew System::Windows::Forms::RadioButton());
			this->MenuPrincipal->SuspendLayout();
			this->tableLayoutPanel1->SuspendLayout();
			this->tabControlGraph->SuspendLayout();
			this->tabPage0->SuspendLayout();
			this->tableLayoutPanel2->SuspendLayout();
			this->tabPage4->SuspendLayout();
			this->SuspendLayout();
			// 
			// MenuPrincipal
			// 
			this->MenuPrincipal->Items->AddRange(gcnew cli::array< System::Windows::Forms::ToolStripItem^  >(1) {this->archivoToolStripMenuItem});
			this->MenuPrincipal->Location = System::Drawing::Point(0, 0);
			this->MenuPrincipal->Name = L"MenuPrincipal";
			this->MenuPrincipal->Size = System::Drawing::Size(1192, 24);
			this->MenuPrincipal->TabIndex = 1;
			this->MenuPrincipal->Text = L"Menú";
			// 
			// archivoToolStripMenuItem
			// 
			this->archivoToolStripMenuItem->Name = L"archivoToolStripMenuItem";
			this->archivoToolStripMenuItem->Size = System::Drawing::Size(60, 20);
			this->archivoToolStripMenuItem->Text = L"Archivo";
			// 
			// tableLayoutPanel1
			// 
			this->tableLayoutPanel1->ColumnCount = 3;
			this->tableLayoutPanel1->ColumnStyles->Add((gcnew System::Windows::Forms::ColumnStyle(System::Windows::Forms::SizeType::Percent, 
				10)));
			this->tableLayoutPanel1->ColumnStyles->Add((gcnew System::Windows::Forms::ColumnStyle(System::Windows::Forms::SizeType::Percent, 
				80)));
			this->tableLayoutPanel1->ColumnStyles->Add((gcnew System::Windows::Forms::ColumnStyle(System::Windows::Forms::SizeType::Percent, 
				10)));
			this->tableLayoutPanel1->Controls->Add(this->tabControlGraph, 1, 1);
			this->tableLayoutPanel1->Controls->Add(this->rBDelete, 0, 1);
			this->tableLayoutPanel1->Dock = System::Windows::Forms::DockStyle::Fill;
			this->tableLayoutPanel1->Location = System::Drawing::Point(0, 24);
			this->tableLayoutPanel1->Name = L"tableLayoutPanel1";
			this->tableLayoutPanel1->RowCount = 3;
			this->tableLayoutPanel1->RowStyles->Add((gcnew System::Windows::Forms::RowStyle(System::Windows::Forms::SizeType::Percent, 10)));
			this->tableLayoutPanel1->RowStyles->Add((gcnew System::Windows::Forms::RowStyle(System::Windows::Forms::SizeType::Percent, 80)));
			this->tableLayoutPanel1->RowStyles->Add((gcnew System::Windows::Forms::RowStyle(System::Windows::Forms::SizeType::Percent, 10)));
			this->tableLayoutPanel1->Size = System::Drawing::Size(1192, 726);
			this->tableLayoutPanel1->TabIndex = 2;
			// 
			// tabControlGraph
			// 
			this->tabControlGraph->Controls->Add(this->tabPage0);
			this->tabControlGraph->Controls->Add(this->tabPage1);
			this->tabControlGraph->Controls->Add(this->tabPage2);
			this->tabControlGraph->Controls->Add(this->tabPage3);
			this->tabControlGraph->Controls->Add(this->tabPage4);
			this->tabControlGraph->Dock = System::Windows::Forms::DockStyle::Fill;
			this->tabControlGraph->Location = System::Drawing::Point(122, 75);
			this->tabControlGraph->Name = L"tabControlGraph";
			this->tabControlGraph->SelectedIndex = 0;
			this->tabControlGraph->Size = System::Drawing::Size(947, 574);
			this->tabControlGraph->TabIndex = 4;
			// 
			// tabPage0
			// 
			this->tabPage0->Controls->Add(this->tableLayoutPanel2);
			this->tabPage0->Location = System::Drawing::Point(4, 22);
			this->tabPage0->Name = L"tabPage0";
			this->tabPage0->Size = System::Drawing::Size(939, 548);
			this->tabPage0->TabIndex = 4;
			this->tabPage0->Text = L"Selección";
			this->tabPage0->UseVisualStyleBackColor = true;
			// 
			// tableLayoutPanel2
			// 
			this->tableLayoutPanel2->ColumnCount = 3;
			this->tableLayoutPanel2->ColumnStyles->Add((gcnew System::Windows::Forms::ColumnStyle(System::Windows::Forms::SizeType::Percent, 
				48)));
			this->tableLayoutPanel2->ColumnStyles->Add((gcnew System::Windows::Forms::ColumnStyle(System::Windows::Forms::SizeType::Percent, 
				4)));
			this->tableLayoutPanel2->ColumnStyles->Add((gcnew System::Windows::Forms::ColumnStyle(System::Windows::Forms::SizeType::Percent, 
				48)));
			this->tableLayoutPanel2->Controls->Add(this->panelTab0Izq, 0, 0);
			this->tableLayoutPanel2->Controls->Add(this->panelTab0Der, 2, 0);
			this->tableLayoutPanel2->Controls->Add(this->listView1, 0, 1);
			this->tableLayoutPanel2->Controls->Add(this->rbCreateMove, 1, 0);
			this->tableLayoutPanel2->Dock = System::Windows::Forms::DockStyle::Fill;
			this->tableLayoutPanel2->Location = System::Drawing::Point(0, 0);
			this->tableLayoutPanel2->Name = L"tableLayoutPanel2";
			this->tableLayoutPanel2->RowCount = 2;
			this->tableLayoutPanel2->RowStyles->Add((gcnew System::Windows::Forms::RowStyle(System::Windows::Forms::SizeType::Percent, 80)));
			this->tableLayoutPanel2->RowStyles->Add((gcnew System::Windows::Forms::RowStyle(System::Windows::Forms::SizeType::Percent, 20)));
			this->tableLayoutPanel2->Size = System::Drawing::Size(939, 548);
			this->tableLayoutPanel2->TabIndex = 0;
			// 
			// panelTab0Izq
			// 
			this->panelTab0Izq->BackColor = System::Drawing::Color::GhostWhite;
			this->panelTab0Izq->BorderStyle = System::Windows::Forms::BorderStyle::FixedSingle;
			this->panelTab0Izq->Cursor = System::Windows::Forms::Cursors::Hand;
			this->panelTab0Izq->Dock = System::Windows::Forms::DockStyle::Fill;
			this->panelTab0Izq->Location = System::Drawing::Point(3, 3);
			this->panelTab0Izq->Name = L"panelTab0Izq";
			this->panelTab0Izq->Size = System::Drawing::Size(444, 432);
			this->panelTab0Izq->TabIndex = 5;
			this->panelTab0Izq->MouseMove += gcnew System::Windows::Forms::MouseEventHandler(this, &SistemaControl::panelTab0Izq_MouseMove);
			this->panelTab0Izq->MouseDown += gcnew System::Windows::Forms::MouseEventHandler(this, &SistemaControl::panelTab0Izq_MouseDown);
			this->panelTab0Izq->MouseUp += gcnew System::Windows::Forms::MouseEventHandler(this, &SistemaControl::panelTab0Izq_MouseUp);
			// 
			// panelTab0Der
			// 
			this->panelTab0Der->AutoScroll = true;
			this->panelTab0Der->BackColor = System::Drawing::SystemColors::WindowFrame;
			this->panelTab0Der->BorderStyle = System::Windows::Forms::BorderStyle::FixedSingle;
			this->panelTab0Der->Dock = System::Windows::Forms::DockStyle::Fill;
			this->panelTab0Der->Location = System::Drawing::Point(490, 3);
			this->panelTab0Der->Name = L"panelTab0Der";
			this->panelTab0Der->Size = System::Drawing::Size(446, 432);
			this->panelTab0Der->TabIndex = 6;
			// 
			// listView1
			// 
			this->listView1->Columns->AddRange(gcnew cli::array< System::Windows::Forms::ColumnHeader^  >(2) {this->columnHeader1, this->columnHeader2});
			this->listView1->Dock = System::Windows::Forms::DockStyle::Fill;
			listViewGroup5->Header = L"Modo Operación";
			listViewGroup5->Name = L"lvgModoOperacion";
			listViewGroup6->Header = L"Información";
			listViewGroup6->Name = L"lvwInformacion";
			this->listView1->Groups->AddRange(gcnew cli::array< System::Windows::Forms::ListViewGroup^  >(2) {listViewGroup5, listViewGroup6});
			this->listView1->HoverSelection = true;
			listViewItem5->Group = listViewGroup5;
			listViewItem6->Group = listViewGroup6;
			this->listView1->Items->AddRange(gcnew cli::array< System::Windows::Forms::ListViewItem^  >(2) {listViewItem5, listViewItem6});
			this->listView1->Location = System::Drawing::Point(3, 441);
			this->listView1->Name = L"listView1";
			this->listView1->Size = System::Drawing::Size(444, 104);
			this->listView1->TabIndex = 7;
			this->listView1->UseCompatibleStateImageBehavior = false;
			this->listView1->View = System::Windows::Forms::View::SmallIcon;
			// 
			// columnHeader1
			// 
			this->columnHeader1->Text = L"Modos Operacion";
			this->columnHeader1->Width = 100;
			// 
			// columnHeader2
			// 
			this->columnHeader2->Text = L"Tipo Trampa";
			this->columnHeader2->Width = 100;
			// 
			// rbCreateMove
			// 
			this->rbCreateMove->AutoSize = true;
			this->rbCreateMove->Location = System::Drawing::Point(453, 3);
			this->rbCreateMove->Name = L"rbCreateMove";
			this->rbCreateMove->Size = System::Drawing::Size(31, 17);
			this->rbCreateMove->TabIndex = 8;
			this->rbCreateMove->TabStop = true;
			this->rbCreateMove->Text = L"Create";
			this->rbCreateMove->TextAlign = System::Drawing::ContentAlignment::BottomLeft;
			this->rbCreateMove->UseVisualStyleBackColor = true;
			this->rbCreateMove->CheckedChanged += gcnew System::EventHandler(this, &SistemaControl::rbCreateMove_CheckedChanged);
			// 
			// tabPage1
			// 
			this->tabPage1->Location = System::Drawing::Point(4, 22);
			this->tabPage1->Name = L"tabPage1";
			this->tabPage1->Padding = System::Windows::Forms::Padding(3);
			this->tabPage1->Size = System::Drawing::Size(939, 548);
			this->tabPage1->TabIndex = 0;
			this->tabPage1->Text = L"AccionAndMask";
			this->tabPage1->UseVisualStyleBackColor = true;
			// 
			// tabPage2
			// 
			this->tabPage2->Location = System::Drawing::Point(4, 22);
			this->tabPage2->Name = L"tabPage2";
			this->tabPage2->Padding = System::Windows::Forms::Padding(3);
			this->tabPage2->Size = System::Drawing::Size(939, 548);
			this->tabPage2->TabIndex = 1;
			this->tabPage2->Text = L"VideoAndMask";
			this->tabPage2->UseVisualStyleBackColor = true;
			// 
			// tabPage3
			// 
			this->tabPage3->Location = System::Drawing::Point(4, 22);
			this->tabPage3->Name = L"tabPage3";
			this->tabPage3->Padding = System::Windows::Forms::Padding(3);
			this->tabPage3->Size = System::Drawing::Size(939, 548);
			this->tabPage3->TabIndex = 2;
			this->tabPage3->Text = L"VidAccAndMask";
			this->tabPage3->UseVisualStyleBackColor = true;
			// 
			// tabPage4
			// 
			this->tabPage4->Controls->Add(this->webBrowser1);
			this->tabPage4->Location = System::Drawing::Point(4, 22);
			this->tabPage4->Name = L"tabPage4";
			this->tabPage4->Padding = System::Windows::Forms::Padding(3);
			this->tabPage4->Size = System::Drawing::Size(939, 548);
			this->tabPage4->TabIndex = 3;
			this->tabPage4->Text = L"AccionAndInversa";
			this->tabPage4->UseVisualStyleBackColor = true;
			// 
			// webBrowser1
			// 
			this->webBrowser1->Dock = System::Windows::Forms::DockStyle::Fill;
			this->webBrowser1->Location = System::Drawing::Point(3, 3);
			this->webBrowser1->MinimumSize = System::Drawing::Size(20, 20);
			this->webBrowser1->Name = L"webBrowser1";
			this->webBrowser1->Size = System::Drawing::Size(933, 542);
			this->webBrowser1->TabIndex = 0;
			this->webBrowser1->Url = (gcnew System::Uri(L"http://webmail.udec.cl", System::UriKind::Absolute));
			// 
			// bwControl
			// 
			this->bwControl->DoWork += gcnew System::ComponentModel::DoWorkEventHandler(this, &SistemaControl::bwControl_DoWork);
			// 
			// rBDelete
			// 
			this->rBDelete->AutoSize = true;
			this->rBDelete->Location = System::Drawing::Point(3, 75);
			this->rBDelete->Name = L"rBDelete";
			this->rBDelete->Size = System::Drawing::Size(100, 17);
			this->rBDelete->TabIndex = 5;
			this->rBDelete->TabStop = true;
			this->rBDelete->Text = L"Eliminar Trampa";
			this->rBDelete->UseVisualStyleBackColor = true;
			this->rBDelete->CheckedChanged += gcnew System::EventHandler(this, &SistemaControl::rBDelete_CheckedChanged);
			// 
			// SistemaControl
			// 
			this->AutoScaleDimensions = System::Drawing::SizeF(6, 13);
			this->AutoScaleMode = System::Windows::Forms::AutoScaleMode::Font;
			this->ClientSize = System::Drawing::Size(1192, 750);
			this->Controls->Add(this->tableLayoutPanel1);
			this->Controls->Add(this->MenuPrincipal);
			this->MinimumSize = System::Drawing::Size(800, 600);
			this->Name = L"SistemaControl";
			this->ShowInTaskbar = false;
			this->Text = L"Sistema de Control";
			this->Load += gcnew System::EventHandler(this, &SistemaControl::SistemaControl_Load);
			this->FormClosed += gcnew System::Windows::Forms::FormClosedEventHandler(this, &SistemaControl::SistemaControl_FormClosed);
			this->MenuPrincipal->ResumeLayout(false);
			this->MenuPrincipal->PerformLayout();
			this->tableLayoutPanel1->ResumeLayout(false);
			this->tableLayoutPanel1->PerformLayout();
			this->tabControlGraph->ResumeLayout(false);
			this->tabPage0->ResumeLayout(false);
			this->tableLayoutPanel2->ResumeLayout(false);
			this->tableLayoutPanel2->PerformLayout();
			this->tabPage4->ResumeLayout(false);
			this->ResumeLayout(false);
			this->PerformLayout();

		}
#pragma endregion
	private: System::Void SistemaControl_Load(System::Object^  sender, System::EventArgs^  e);
	private: System::Void SistemaControl_FormClosed(System::Object^  sender, System::Windows::Forms::FormClosedEventArgs^  e);
	private: System::Void bwControl_DoWork(System::Object^  sender, System::ComponentModel::DoWorkEventArgs^  e);
	private: System::Void panelTab0Izq_MouseDown(System::Object^  sender, System::Windows::Forms::MouseEventArgs^  e);
	private: System::Void panelTab0Izq_MouseMove(System::Object^  sender, System::Windows::Forms::MouseEventArgs^  e);
	private: System::Void panelTab0Izq_MouseUp(System::Object^  sender, System::Windows::Forms::MouseEventArgs^  e);
	private: System::Void rbCreateMove_CheckedChanged(System::Object^  sender, System::EventArgs^  e) 
		{
			if(rbCreateMove->Checked)
			{
				rBDelete->Checked = false;
			}
		 };
private: System::Void rBDelete_CheckedChanged(System::Object^  sender, System::EventArgs^  e) 
		 {
			if(rBDelete->Checked)
			{
				rbCreateMove->Checked = false;
			}
		 }
};
}
