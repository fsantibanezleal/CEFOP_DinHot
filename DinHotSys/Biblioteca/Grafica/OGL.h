//---------------------------------------------------------------------------
#pragma once

#pragma hdrstop

#ifndef WINVER				// Allow use of features specific to Windows XP or later.
#define WINVER 0x0501		// Change this to the appropriate value to target other versions of Windows.
#endif

#ifndef _WIN32_WINNT		// Allow use of features specific to Windows XP or later.                   
#define _WIN32_WINNT 0x0501	// Change this to the appropriate value to target other versions of Windows.
#endif						

#ifndef _WIN32_WINDOWS		// Allow use of features specific to Windows 98 or later.
#define _WIN32_WINDOWS 0x0410 // Change this to the appropriate value to target Windows Me or later.
#endif

#ifndef _WIN32_IE			// Allow use of features specific to IE 6.0 or later.
#define _WIN32_IE 0x0600	// Change this to the appropriate value to target other versions of IE.
#endif

#define WIN32_LEAN_AND_MEAN		// Exclude rarely-used stuff from Windows headers
// Windows Header Files:
#include <windows.h>
#include <string>

#include "GL_Camara.h"

using namespace std;

enum{W_ONE,W_TWO,W_THREE};
//---------------------------------------------------------------------------
class OGL
{
protected:
	bool m_selected;
	GL_Camara *CamaraVentana;
	GLfloat LightAmbient[4];
	GLfloat LightDiffuse[4];
	GLfloat LightSpecular[4];
	GLfloat LightPosition[4];

	GLdouble	projection_First[16]; 
	GLdouble	modelview_First[16];
	GLint		viewport_First[4];

	int TYPE_MODELS;
	bool m_show_obb;
	bool m_show_axis;
	float m_radio_centro;

	int m_Width_Windows_main;
	int m_Height_Windows_main;

	stVertex m_origen, center_box, pos_eye_camara;
	float m_ancho,m_alto,m_largo;

	GLuint	base;				// Base Display List For The Font Set
	int m_ventana;
	int Key_Status;
	int Key_Status_Save;
public:

		HWND		hwnd;
		HDC			hdc;	//Manipulador Ventana
		HGLRC		hrc;    //Manipulador OpenGL

		OGL(){};
		
		~OGL()
		{
			Destruir();
		};

		// Funciones de selccion de contexto
		virtual void Crear(HWND MyHwnd, int v);
		virtual void Destruir();
		virtual bool SetActual();
		virtual void DestruirFont(void);

		// Funciones de renderizacion
		virtual void InitOpenGL();
		virtual void Resize(int w, int h);


		virtual void SetLight(bool setluz=true);
		virtual void Renderizar();
		virtual void glDrawAxis(void);
		virtual int GetSelected(void){return m_selected;}
		virtual void SetSelected(bool s){m_selected=s;}
		virtual void KeyBoard(int key);
		virtual void SaveKeyBoard(void){Key_Status_Save=Key_Status;};
		virtual int GetSaveStatusKeyBoard(void){return Key_Status_Save;};
		virtual void SetSmoothFlat(bool v){if(v)TYPE_MODELS=GL_SMOOTH;else TYPE_MODELS=GL_FLAT;}
		virtual void ShowObb(bool v){m_show_obb=v;}
		virtual void ShowAxis(bool v){m_show_axis=v;}
		virtual void MouseMove(int x, int y);
		virtual void MouseLButtonDown(int x, int y);
		virtual void MouseLButtonUp(int x, int y);
		virtual stVertex GetCenterBox(void){return center_box;}
		virtual stVertex GetEyeCamara(void){return CamaraVentana->GetCamViewXYZ();}
		virtual void SetEyeCamara(stVertex e){pos_eye_camara=e;CamaraVentana->SetCamViewXYZ(e.x,e.y,e.z);}
		virtual void SetOrigenEyeCamara(int x,int y, int z){CamaraVentana->SetOrigenEye(x,y,z);}
		virtual void SetOrigenCenterCamara(int x,int y, int z){CamaraVentana->SetOrigenCenter(x,y,z);}
		virtual void SetCenterBox(stVertex c){center_box=c;CamaraVentana->SetCamAtXYZ(c.x,c.y,c.z);}
		virtual void SetRadioCenterView(float r){m_radio_centro=r;}
		virtual	void ResetCenterCamara(void){CamaraVentana->SetCamAtXYZ(center_box.x,center_box.y,center_box.z);
		CamaraVentana->SetCamViewXYZ(pos_eye_camara.x,pos_eye_camara.y,pos_eye_camara.z);}
		void ViewportCircular(float factor=1.0, int angulo = 1);
		void Print(float color[3], float x, float y,  string nombre);
		GLvoid BuildFont(int dim	= 24);
		int GetVentana(void){return m_ventana;}
		void SetVentana(int v){m_ventana=v;}
		virtual void OnOffDrawWorld(bool s){CamaraVentana->OnOffDrawWorld(s);}
		virtual void SetCameraNearFarAngle(float n, float f, float a);
		virtual stVertex GetPositionLight(void){stVertex temp; SetFull(temp,LightPosition[0],LightPosition[1],LightPosition[2]); return temp;}
		virtual int GetKeyStatus(void){return Key_Status;}
};
