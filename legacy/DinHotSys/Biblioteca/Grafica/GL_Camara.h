#pragma once

//#include <GL/glew.h>
#include <GL/glut.h>
#include <GL/gl.h>
#include "BasicFunctions.h"

#define CAM_PARALLEL 1
#define CAM_CONIC	2

#define CAM_STOP 0
#define CAM_EXAMINAR 1
#define CAM_PASEAR 2
#define CAM_TRIPODE 3
#define CAM_PAN 4


#include <math.h>
#
#ifndef TRUE
#define TRUE   1
#define FALSE  0
#endif

#ifndef NULL
#define NULL  0
#endif


// *** Mathematics
#define VECTOR_EPSILON    0.00001f
#define DISTANCE_EPSILON  1e-08f
#define ANGLE_EPSILON     0.00872665f  // 0.5 degrees

#define MOD(A,B,C) (float) sqrt( A*A + B*B + C*C )

#define PI_VALUE           3.14159265359f
#define DEGREE_TO_RAD      0.0174533f /* 2.0 * 3.1415927 / 360.0 */
#define RAD_TO_DEGREE     57.2958f    /* 360 / ( 2.0 * 3.1415927 ) */

enum{KEY_M_NONE,KEY_M_L_DOWN,KEY_M_L_UP,KEY_M_R_DOWN,KEY_M_R_UP};
enum{KEY_T_NONE,KEY_T_F1,KEY_T_F2,KEY_T_F3,KEY_T_F4,KEY_T_HOME};
enum{H_ZOOM_IN,H_ZOOM_OUT,H_ZOOM_NONE};
class GL_Camara
{
private:
	bool m_show_world;
	bool m_haptic_set;
	int PosEyeX,PosEyeY,PosEyeZ;
	int PosCentX,PosCentY,PosCentZ;

	int state;
	bool m_MouseMotion;
	bool m_Examinar;
	bool m_Andar;
	bool m_Zoom;
	bool m_Selection;
	bool m_Selection_Objet;
	bool m_Seleccion_Slice;
	bool m_camara_move;

	stVertex camView, camAt, camUp;

	float	 camAperture;

	float	 camNear;
	float	 camFar;
	int		 camProjection;	// PARALLEL or CONIC
	int		 camMovimiento; // EXAMINAR, ANDAR, TRIPODE or PAN
	float	ancho;

	float	 aspectRatio;

	// para proyeccion ortogonal
	float	 x1, x2, y1, y2, z1, z2,W,H,fact_W,fact_H;

	// camara i j k vectores en cordenadas de mundo
	stVertex camI, camJ, camK;

	// variables del mouse
	int old_x;
	int old_y;
	bool up_down;

	float Width;
	float Height;

	float m_proyection_invertida[16];

	GLfloat		look_matrix[16];
	GLfloat		projection[16];
	GLfloat		modelview[16];
	GLint		viewport[4];

	int ID_VENTANA;
public:
	GL_Camara(float positionX, float positionY, float positionZ);
	~GL_Camara(void);

	void  SetCamera( float viewX, float viewY, float viewZ,
			float atX,   float atY,   float atZ,
			float upX,   float upY,   float upZ );
	void SetDependentParametersCamera(void);
	void SetGLCamera(void);
	void SetGLAspectRatioCamera(void);
	void MouseMotion(int x, int y);
	void Examinar(int x, int y);
	void SetOldXY(int x, int y);
	void Andar(int x, int y);
	void Zoom(int x, int y);

	void  AvanceFreeCamera(float step );

// ROTATION
	void  YawCamera(float angle );			// local axis Y camera

	void Rotar_Latitud(float inc );
	void Rotar_Longitud(float inc );
	void Rotar(float inc_x, float inc_y);
	void GetMatrix(GLdouble *m, GLdouble *p, GLint *v);

	void VectorRotY( float *vIn, float inc );
	void VectorRotXZ( float *vIn, float inc, int flagStop );
	void VectorRot( float *vIn, float inc_x, float inc_y);

	//=================================================================
	void GetZoomView(float *x,float *y){*x=fact_W;*y=fact_H;}
	void SetZoomView(float  x,float  y){fact_W=x; fact_H=y;}
	void ResetZoom(void){fact_W=fact_H=0.05;}
	void SetViewport(float w, float h){Width=w;Height=h;}
	void SetCamAtY(float y){camAt.y=y;}
	void SetCamViewY(float y){camView.y=y;}
	void SetCamAt(float x,float y, float z){camAt.x=x;camAt.y=y;camAt.z=z;}
	void SetCamViewXYZ(float x,float y, float z){camView.x = x;camView.y = y;camView.z = z;SetDependentParametersCamera();}
	void GetCamViewXYZ(float *x,float *y, float *z){*x=camView.x-camAt.x;*y=camView.y-camAt.y;*z=camView.z-camAt.z;}
	stVertex GetCamDirView(void){return Resta(camView,camAt);}
	stVertex GetCamViewXYZ(void){return camView;}
	stVertex GetCamViewCenter(void){return camAt;}
	void GetCamAtXYZ(float *x,float *y, float *z){*x=camAt.x;*y=camAt.y;*z=camAt.z;}
	void SetCamAtXYZ(float x,float y, float z){camAt.x = x;camAt.y = y;camAt.z = z;SetDependentParametersCamera();}
	int  GetCamMovimiento(void){return camMovimiento;}
	void SetCamMovimiento(int mov){camMovimiento=mov;}
	void ClickMouse(int x, int y);
	void KeyBoard(int key);
	void MouseMove(int x, int y);
	void SetEstado(int s){state=s;}
	void SetIdVentana(int i){ID_VENTANA=i;}
	int GetIdVentana(void){return ID_VENTANA;}

	//void GetInvMatrix(float** m){*m = inv_look->values;}//Parte diego
	void GetInvMatrix(float* m);
	void GetDirMatrix(float* m);
	bool InversaLU(float *m_origen);
	void SetParametrosHapticos(stVertex _h_Eye,stVertex _h_Center,stVertex _h_Up);
	void OnOffHapticCamera(bool v){m_haptic_set=v;}
	void ZoomHaptic(int tipo);
	void glDrawViewPort(void);
	GLboolean invert(GLdouble src[16], GLdouble inverse[16]);
	void identity(GLdouble m[16]);
	stVertex GetCamUp(void){return camUp;}
	stVertex GetCamJ(void){return camJ;}
	stVertex GetCamK(void){return camK;}
	stVertex GetCamI(void){return camI;}
	void SetCameraPrejection(int p){camProjection=p;}
	void MultMxV(float *_C, float *A, float *_B);
	bool GetCamaraMove(void){return m_camara_move;}
	void SetCameraNear(float s){camNear=s;}
	void SetCameraFar(float s){camFar=s;}
	float GetCameraNear(void){return camNear;}
	float GetCameraFar(void){return camFar;}
	void SetCameraApertura(float s){camAperture=s*DEGREE_TO_RAD;}
	float GetCameraApertura(void){return (camAperture*RAD_TO_DEGREE);}
	bool GetOnOffDrawWorld(void){return m_show_world;}
	void OnOffDrawWorld(bool s){m_show_world=s;}
	void SetOrigenCenter(int x,int y,int z){PosCentX=x;PosCentY=y;PosCentZ=z;}
	void SetOrigenEye(int x,int y,int z){PosEyeX=x;PosEyeY=y;PosEyeZ=z;}
};
