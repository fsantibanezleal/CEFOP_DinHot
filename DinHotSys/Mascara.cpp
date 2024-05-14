#include "Principal.h"
#include "Mascara.h"
#include "GL_Mascaras.h"

using namespace DinHotSys;

GL_Mascaras ventanaMascaraGlCentral;

System::Void Mascara::Mascara_Load(System::Object^  sender, System::EventArgs^  e)
{
	if(((Principal ^)_ventanaPrincipal)->mutexOGL->WaitOne()) // No realmente necesario.. aun no empiezan a correr las otras hebras
	{
		wglMakeCurrent (NULL, NULL);
		ventanaMascaraGlCentral.Crear( reinterpret_cast<HWND> (this->Handle.ToPointer()),W_TWO);	

		wglMakeCurrent (NULL, NULL);
	
		((Principal ^)_ventanaPrincipal)->mutexOGL->ReleaseMutex();
	}

	bwCalcMask->RunWorkerAsync();
};

System::Void Mascara::bwCalcMask_DoWork(System::Object^  sender, System::ComponentModel::DoWorkEventArgs^  e)
{
	_masker = new MatDinHot();
	while(!bwCalcMask->CancellationPending)
	{
		if(((Principal ^)_ventanaPrincipal)->mutexOGL->WaitOne()) // No realmente necesario.. aun no empiezan a correr las otras hebras
		{
			if(ventanaMascaraGlCentral.SetActual())
			{
				//_masker->SetResPantalla(this->Width,this->Height);
				//_masker->SetNumTrampas(((SistemaControl ^)((Principal ^)_ventanaPrincipal)->_ventanaControl)->_masker->GetNumTrampas());
				//_masker->SetPosTrampas(((SistemaControl ^)((Principal ^)_ventanaPrincipal)->_ventanaControl)->_masker->GetPosTrampas());
				_masker->CalcMatriz();
				ventanaMascaraGlCentral.Resize(this->Width,this->Height,_masker->GetResX(),_masker->GetResY());
				ventanaMascaraGlCentral.Renderizar(_masker->GetPhi(),_masker->GetResX(),_masker->GetResY());
			}
			((Principal ^)_ventanaPrincipal)->mutexOGL->ReleaseMutex();
		}
	}
};

