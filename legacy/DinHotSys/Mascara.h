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
	/// Summary for Mascara
	///
	/// WARNING: If you change the name of this class, you will need to change the
	///          'Resource File Name' property for the managed resource compiler tool
	///          associated with all .resx files this class depends on.  Otherwise,
	///          the designers will not be able to interact properly with localized
	///          resources associated with this form.
	/// </summary>
	public ref class Mascara : public System::Windows::Forms::Form
	{
	public:		MatDinHot *_masker;
	private:	System::Windows::Forms::Form ^_ventanaPrincipal;
	public:
		Mascara(void)
		{
			InitializeComponent();
			//
			//TODO: Add the constructor code here
			//
		}
		Mascara(System::Windows::Forms::Form ^vPrincipal)
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
		~Mascara()
		{
			if (components)
			{
				delete components;
			}
		}
	private: System::ComponentModel::BackgroundWorker^  bwCalcMask;
	protected: 

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
			this->bwCalcMask = (gcnew System::ComponentModel::BackgroundWorker());
			this->SuspendLayout();
			// 
			// bwCalcMask
			// 
			this->bwCalcMask->DoWork += gcnew System::ComponentModel::DoWorkEventHandler(this, &Mascara::bwCalcMask_DoWork);
			// 
			// Mascara
			// 
			this->AutoScaleDimensions = System::Drawing::SizeF(6, 13);
			this->AutoScaleMode = System::Windows::Forms::AutoScaleMode::Font;
			this->BackColor = System::Drawing::SystemColors::WindowFrame;
			this->ClientSize = System::Drawing::Size(800, 600);
			this->ControlBox = false;
			this->Cursor = System::Windows::Forms::Cursors::Cross;
			this->FormBorderStyle = System::Windows::Forms::FormBorderStyle::None;
			this->MaximizeBox = false;
			this->MinimizeBox = false;
			this->Name = L"Mascara";
			this->ShowInTaskbar = false;
			this->Text = L"Mascara";
			this->TopMost = true;
			this->Load += gcnew System::EventHandler(this, &Mascara::Mascara_Load);
			this->MouseEnter += gcnew System::EventHandler(this, &Mascara::Mascara_MouseEnter);
			this->MouseLeave += gcnew System::EventHandler(this, &Mascara::Mascara_MouseLeave);
			this->ResumeLayout(false);

		}
#pragma endregion
	private: System::Void Mascara_Load(System::Object^  sender, System::EventArgs^  e);
	private: System::Void bwCalcMask_DoWork(System::Object^  sender, System::ComponentModel::DoWorkEventArgs^  e);
	private: System::Void Mascara_MouseEnter(System::Object^  sender, System::EventArgs^  e) 
			 {
				 Cursor->Hide();
			 }
	private: System::Void Mascara_MouseLeave(System::Object^  sender, System::EventArgs^  e) 
			 {
				 Cursor->Show();
			 }
	};
}
