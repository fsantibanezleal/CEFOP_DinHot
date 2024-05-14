#include "GL_Trampas.h"

GL_Trampas::GL_Trampas(void)
{
};

GL_Trampas::~GL_Trampas(void)
{
};

void GL_Trampas::Resize(int vDimVentanaX, int vDimVentanaY)
{
	register float dimEspacio = 400.0f;
	m_Width_Windows_main = vDimVentanaX;
	m_Height_Windows_main = vDimVentanaY;
	glViewport(0, 0, m_Width_Windows_main, m_Height_Windows_main);
	
	glMatrixMode( GL_PROJECTION );
	glLoadIdentity( );

	glOrtho(-dimEspacio/2.0f,dimEspacio/2.0f,-dimEspacio/2.0f,dimEspacio/2.0f,-3000,3000);

	stVertex ojo;
	SetFull(ojo,0.0f,0.0f,1.0f);

	gluLookAt(	ojo.x, ojo.y, ojo.z, 
				ojo.x, ojo.y, 0.0f,
				0.0f,  1.0f,  0.0f);

	glMatrixMode( GL_MODELVIEW );	// *** GL_MODELVIEW ***
	glLoadIdentity();
};

void GL_Trampas::Renderizar(stVertex *vPosicionTrampas,unsigned vNumTrampas)
{
	register unsigned i;

	glClearColor(125/255.0f, 136/255.0f, 232/255.0f, 1.0f);
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
	glEnable(GL_DEPTH_TEST);
	glEnable(GL_LIGHTING);
	//CamaraVentana->SetGLCamera();
	//CamaraVentana ->GetMatrix(modelview_First,projection_First,viewport_First);
	//CamaraVentana->GetInvMatrix(inv_projection);
	
	SetLight();
	// dibujar

	glPointSize(10.0f);
	glBegin(GL_POINTS);
	for(i = 0; i < vNumTrampas; i++)
	{
		glColor3f(1,0,0);
		glVertex3f(factorDim*vPosicionTrampas[i].x,factorDim*vPosicionTrampas[i].y,factorDim*vPosicionTrampas[i].z);
	}
	glEnd();
	glPointSize(1.0f);
	
	//glDrawAxis();
	glFlush();
	SwapBuffers(hdc);
};
