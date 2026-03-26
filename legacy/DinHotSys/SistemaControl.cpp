#include "Principal.h"

#include "SistemaControl.h"
#include "Mascara.h"

#include "GL_Trampas.h"
#include "GL_Mascaras.h"

using namespace DinHotSys;

GL_Trampas	ventanaTrampaGl;
GL_Mascaras ventanaMascaraGl;

System::Void SistemaControl::SistemaControl_Load(System::Object^  sender, System::EventArgs^  e)
{
	if(((Principal ^)_ventanaPrincipal)->mutexOGL->WaitOne()) // No realmente necesario.. aun no empiezan a correr las otras hebras
	{
		wglMakeCurrent (NULL, NULL);
		ventanaTrampaGl.Crear( reinterpret_cast<HWND> (panelTab0Izq->Handle.ToPointer()),W_ONE);	
		ventanaMascaraGl.Crear( reinterpret_cast<HWND> (panelTab0Der->Handle.ToPointer()),W_TWO);	

		wglMakeCurrent (NULL, NULL);
	
		((Principal ^)_ventanaPrincipal)->mutexOGL->ReleaseMutex();
	}

	bwControl->RunWorkerAsync();
};

System::Void SistemaControl::SistemaControl_FormClosed(System::Object^  sender, System::Windows::Forms::FormClosedEventArgs^  e) 
{
	((Principal ^)_ventanaPrincipal)->Show();
};

System::Void SistemaControl::bwControl_DoWork(System::Object^  sender, System::ComponentModel::DoWorkEventArgs^  e)
{
	_masker = new MatDinHot();
	while(!bwControl->CancellationPending)
	{
		// Funcion de pintado seleccion de contexto de dibujo actual
		if(((Principal ^)_ventanaPrincipal)->mutexOGL->WaitOne())
		{
			if(ventanaTrampaGl.SetActual())
			{
				ventanaTrampaGl.Resize(panelTab0Izq->Width,panelTab0Izq->Height);
				ventanaTrampaGl.Renderizar(_masker->GetPosTrampas(),_masker->GetNumTrampas());
			}
			if(ventanaMascaraGl.SetActual())
			{
				_masker->SetResPantalla(panelTab0Izq->Width,panelTab0Izq->Height);
				if(((Mascara ^)((Principal ^)_ventanaPrincipal)->_ventanaMascara)->_masker)
				{
					((Mascara ^)((Principal ^)_ventanaPrincipal)->_ventanaMascara)->_masker->SetResPantalla(panelTab0Izq->Width,panelTab0Izq->Height);
				}
				_masker->CalcMatriz();
				ventanaMascaraGl.Resize(panelTab0Der->Width,panelTab0Der->Height,_masker->GetResX(),_masker->GetResY());
				ventanaMascaraGl.Renderizar(_masker->GetPhi(),_masker->GetResX(),_masker->GetResY());
			}
			((Principal ^)_ventanaPrincipal)->mutexOGL->ReleaseMutex();
		}	
	}
};

System::Void SistemaControl::panelTab0Izq_MouseDown(System::Object^  sender, System::Windows::Forms::MouseEventArgs^  e)
{
	if(rBDelete->Checked)
	{
		_masker->DeleteTrampa((float)e->X,(float)e->Y);
		((Mascara ^)((Principal ^)_ventanaPrincipal)->_ventanaMascara)->_masker->DeleteTrampa((float)e->X,(float)e->Y);
		rBDelete->Checked = false;
	}
	else if(rbCreateMove->Checked)
	{
		_masker->AddTrampa((float)e->X,(float)e->Y);
		((Mascara ^)((Principal ^)_ventanaPrincipal)->_ventanaMascara)->_masker->AddTrampa((float)e->X,(float)e->Y);
		rbCreateMove->Checked = false;
	}
	else if(((Principal ^)_ventanaPrincipal)->mutexOGL->WaitOne())
	{
		_masker->SelectMove((float)e->X,(float)e->Y);
		((Mascara ^)((Principal ^)_ventanaPrincipal)->_ventanaMascara)->_masker->SelectMove((float)e->X,(float)e->Y);
		//((Mascara ^)((Principal ^)_ventanaPrincipal)->_ventanaMascara)->_masker->SelectMove((float)e->X,(float)e->Y);
		((Principal ^)_ventanaPrincipal)->mutexOGL->ReleaseMutex();
	}
};

System::Void SistemaControl::panelTab0Izq_MouseMove(System::Object^  sender, System::Windows::Forms::MouseEventArgs^  e)
{
	if(_masker && e->Button == System::Windows::Forms::MouseButtons::Left)
	{
		_masker->Move((float)e->X,(float)e->Y);
		((Mascara ^)((Principal ^)_ventanaPrincipal)->_ventanaMascara)->_masker->Move((float)e->X,(float)e->Y);
	}
};

System::Void SistemaControl::panelTab0Izq_MouseUp(System::Object^  sender, System::Windows::Forms::MouseEventArgs^  e)
{
	_masker->FreeMove();
	((Mascara ^)((Principal ^)_ventanaPrincipal)->_ventanaMascara)->_masker->FreeMove();
};

