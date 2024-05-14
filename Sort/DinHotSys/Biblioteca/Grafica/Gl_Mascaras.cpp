#include "GL_Mascaras.h"

GL_Mascaras::GL_Mascaras(void)
{
}

GL_Mascaras::~GL_Mascaras(void)
{
}

void GL_Mascaras::Resize(int w, int h)
{
	m_Width_Windows_main=w;
	m_Height_Windows_main=h;
	glViewport(0, 0, m_Width_Windows_main, m_Height_Windows_main);
	
	glMatrixMode( GL_PROJECTION );
	glLoadIdentity( );

	glOrtho(0,m_Width_Windows_main,0,m_Height_Windows_main,-3000,3000);

	stVertex ojo;
	SetFull(ojo,m_Width_Windows_main / 2.0f,m_Height_Windows_main / 2.0f,100.0f);
 	glPushMatrix();
		glLoadIdentity();
	
		gluLookAt(	ojo.x, ojo.y, ojo.z, 
					ojo.x, ojo.y, 0.0f,
					0.0f,  1.0f,  0.0f);
	glPopMatrix();

	glMatrixMode( GL_MODELVIEW );	// *** GL_MODELVIEW ***
	glLoadIdentity();
};

void GL_Mascaras::Resize(unsigned vDimVentanaX, unsigned vDimVentanaY, unsigned vResMaskX, unsigned vResMaskY)
{
	m_Width_Windows_main = vDimVentanaX;
	m_Height_Windows_main = vDimVentanaY;
	glViewport(0, 0, m_Width_Windows_main, m_Height_Windows_main);
	
	glMatrixMode( GL_PROJECTION );
	glLoadIdentity( );

	glOrtho(0,vResMaskX,0,vResMaskY,-3000,3000);

	stVertex ojo;
	SetFull(ojo,(float)vResMaskX / 2.0f,(float)vResMaskY / 2.0f,100.0f);
	SetFull(ojo,(float)0 / 2.0f,(float)0 / 2.0f,100.0f);

	gluLookAt(	ojo.x, ojo.y, ojo.z, 
					ojo.x, ojo.y, 0.0f,
					0.0f,  1.0f,  0.0f);

	glMatrixMode( GL_MODELVIEW );	// *** GL_MODELVIEW ***
	glLoadIdentity();
};

void GL_Mascaras::Renderizar(float** vMatriz,unsigned vX, unsigned vY)
{
	register unsigned i,j;
	register float colorGris;
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
	glEnable(GL_DEPTH_TEST);
	//glEnable(GL_LIGHTING);
	glDisable(GL_LIGHTING);
	//CamaraVentana->SetCameraPrejection(CAM_PARALLEL);
	//CamaraVentana->SetGLCamera();
//	CamaraVentana ->GetMatrix(modelview_First,projection_First,viewport_First);
//	CamaraVentana->GetInvMatrix(inv_projection);
	//SetLight();
	//// dibujar

	glPointSize(1.0f);
	glBegin(GL_POINTS);
	for(i = 0; i < vX; i++)
	{
		for(j = 0; j < vY; j++)
		{
			colorGris = vMatriz[i][j];
			glColor3f(colorGris,colorGris,colorGris);
			glVertex3f((float)i,(float)j, 0.0f);
		}
	}
	glEnd();

	glFlush();
	SwapBuffers(hdc);
};

//void GL_Mascaras::Renderizar(float** vMatriz,unsigned vDimVentanaX, unsigned vDimVentanaY, unsigned vResMaskX, unsigned vResMaskY)
//{
//	register unsigned i,j;
//	register float colorGris,factorX,factorY;
//	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
//	glEnable(GL_DEPTH_TEST);
//	//glEnable(GL_LIGHTING);
//	glDisable(GL_LIGHTING);
//	//CamaraVentana->SetCameraPrejection(CAM_PARALLEL);
//	//CamaraVentana->SetGLCamera();
////	CamaraVentana ->GetMatrix(modelview_First,projection_First,viewport_First);
////	CamaraVentana->GetInvMatrix(inv_projection);
//	//SetLight();
//	//// dibujar
//
//	factorX = (float)vResMaskX / (float)vDimVentanaX;
//	factorY = (float)vResMaskY / (float)vDimVentanaY;
//
//	glPointSize(1.0f);
//	glBegin(GL_POINTS);
//	for(i = 0; i < vDimVentanaX; i++)
//	{
//		for(j = 0; j < vDimVentanaY; j++)
//		{
//			colorGris = 1;//vMatriz[i][j];
//			glColor3f(colorGris,0,0);
//			glVertex3f((float)i,(float)j, 0.0f);
//		}
//	}
//	glEnd();
//
//	glFlush();
//	SwapBuffers(hdc);
//};