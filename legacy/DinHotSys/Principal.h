#pragma once

#include "Mascara.h"
#include "SistemaControl.h"

namespace DinHotSys {

	using namespace System;
	using namespace System::ComponentModel;
	using namespace System::Collections;
	using namespace System::Windows::Forms;
	using namespace System::Data;
	using namespace System::Drawing;
	using namespace System::Threading; // para los mutex
	using namespace System::Runtime::InteropServices;

	/// <summary>
	/// Summary for Form1
	///
	/// WARNING: If you change the name of this class, you will need to change the
	///          'Resource File Name' property for the managed resource compiler tool
	///          associated with all .resx files this class depends on.  Otherwise,
	///          the designers will not be able to interact properly with localized
	///          resources associated with this form.
	/// </summary>
	public ref class Principal : public System::Windows::Forms::Form
	{
	public:
		Principal(void)
		{
			InitializeComponent();
			//
			//TODO: Add the constructor code here
			//
		}

	protected:
		/// <summary>
		/// Clean up any resources being used.
		/// </summary>
		~Principal()
		{
			if (components)
			{
				delete components;
			}
		}
	private: System::ComponentModel::IContainer^  components;
	private: System::Windows::Forms::PictureBox^  pictureBoxIni;
	private: System::Windows::Forms::ProgressBar^  progressBarIni;

	private: System::Windows::Forms::Button^  button1;

	public: Mutex	^mutexOGL,^mutexDatos;
	public: Mascara		^_ventanaMascara;
	public: SistemaControl	^_ventanaControl;
	private:
		/// <summary>
		/// Required designer variable.
		/// </summary>


#pragma region Windows Form Designer generated code
		/// <summary>
		/// Required method for Designer support - do not modify
		/// the contents of this method with the code editor.
		/// </summary>
		void InitializeComponent(void)
		{
			this->pictureBoxIni = (gcnew System::Windows::Forms::PictureBox());
			this->progressBarIni = (gcnew System::Windows::Forms::ProgressBar());
			this->button1 = (gcnew System::Windows::Forms::Button());
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^  >(this->pictureBoxIni))->BeginInit();
			this->SuspendLayout();
			// 
			// pictureBoxIni
			// 
			this->pictureBoxIni->Location = System::Drawing::Point(12, 30);
			this->pictureBoxIni->Name = L"pictureBoxIni";
			this->pictureBoxIni->Size = System::Drawing::Size(165, 211);
			this->pictureBoxIni->TabIndex = 0;
			this->pictureBoxIni->TabStop = false;
			// 
			// progressBarIni
			// 
			this->progressBarIni->Location = System::Drawing::Point(202, 218);
			this->progressBarIni->Name = L"progressBarIni";
			this->progressBarIni->Size = System::Drawing::Size(168, 23);
			this->progressBarIni->Step = 1;
			this->progressBarIni->TabIndex = 1;
			// 
			// button1
			// 
			this->button1->FlatAppearance->BorderColor = System::Drawing::Color::Navy;
			this->button1->FlatAppearance->BorderSize = 3;
			this->button1->FlatAppearance->MouseDownBackColor = System::Drawing::Color::FromArgb(static_cast<System::Int32>(static_cast<System::Byte>(64)), 
				static_cast<System::Int32>(static_cast<System::Byte>(64)), static_cast<System::Int32>(static_cast<System::Byte>(64)));
			this->button1->FlatAppearance->MouseOverBackColor = System::Drawing::Color::Gray;
			this->button1->FlatStyle = System::Windows::Forms::FlatStyle::System;
			this->button1->Location = System::Drawing::Point(254, 151);
			this->button1->Name = L"button1";
			this->button1->Size = System::Drawing::Size(75, 41);
			this->button1->TabIndex = 2;
			this->button1->Text = L"Lanzar Aplicacion";
			this->button1->UseVisualStyleBackColor = true;
			this->button1->Click += gcnew System::EventHandler(this, &Principal::button1_Click);
			// 
			// Principal
			// 
			this->AutoScaleDimensions = System::Drawing::SizeF(6, 13);
			this->AutoScaleMode = System::Windows::Forms::AutoScaleMode::Font;
			this->ClientSize = System::Drawing::Size(394, 276);
			this->Controls->Add(this->button1);
			this->Controls->Add(this->progressBarIni);
			this->Controls->Add(this->pictureBoxIni);
			this->FormBorderStyle = System::Windows::Forms::FormBorderStyle::FixedToolWindow;
			this->Name = L"Principal";
			this->ShowInTaskbar = false;
			this->Text = L"Gestor Sistema: Dinamic Hot System v 0.1.2----> Init";
			this->Load += gcnew System::EventHandler(this, &Principal::Principal_Load);
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^  >(this->pictureBoxIni))->EndInit();
			this->ResumeLayout(false);

		}
#pragma endregion
	private: System::Void Principal_Load(System::Object^  sender, System::EventArgs^  e)
			 {
				 mutexOGL	=	gcnew Mutex;
				 mutexDatos	=	gcnew Mutex;
				 pictureBoxIni->ImageLocation = "Multimedia/b600157m-350_tcm18-60383.jpg";
				 //pictureBoxIni->SizeMode = PictureBoxSizeMode::AutoSize;
			 }
	private: System::Void button1_Click(System::Object^  sender, System::EventArgs^  e) 
			 {
				register unsigned i,j;

				i = j = 0;
				while(progressBarIni->Value < progressBarIni->Maximum)
				{
					j++;
					if(j > 1000000)
					{
						progressBarIni->Increment(1);
						j = 0;
					}
					i++;
				};

				this->Hide();
				_ventanaMascara =	gcnew Mascara(this);
				_ventanaControl =	gcnew SistemaControl(this);

				_ventanaControl->Show();
				_ventanaControl->WindowState=FormWindowState::Maximized;
				_ventanaControl->BringToFront();

				_ventanaMascara->Show();

				if(SystemInformation::MonitorCount > 1)
				{
					_ventanaMascara->Location = Point(SystemInformation::PrimaryMonitorSize.Width,0);
					//_ventanaMascara->Location = Point(GetSystemMetrics(SM_CXSCREEN),0);
					_ventanaMascara->WindowState=FormWindowState::Maximized;
					_ventanaMascara->BringToFront();
				}
				else
				{
					_ventanaMascara->TopMost = false;
					_ventanaControl->BringToFront();
				}

				_ventanaMascara->Text = "Mask: Iniciada";

				progressBarIni->Value = progressBarIni->Minimum;
			 }
};
}

