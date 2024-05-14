#include "GL_Camara.h"

#pragma comment(lib, "opengl32.lib")
#pragma comment(lib, "glu32.lib")
#pragma comment(lib, "glaux.lib")

#include <gl\glaux.h>
//#include <GL/glew.h>
#include <GL/glut.h>
#include <GL/glu.h>
#include <GL/gl.h>

GL_Camara::GL_Camara(float positionX, float positionY, float positionZ)
{
	m_show_world=false;
	m_camara_move=false;
	m_haptic_set=false;
	ID_VENTANA=0;
	state=KEY_M_NONE;
	m_MouseMotion=false;
	m_Examinar=false;
	m_Andar=false;
	m_Zoom=false;
	m_Selection=true;
	m_Selection_Objet=false;
	m_Seleccion_Slice=false;
	PosEyeX=positionX;
	PosEyeY=positionY;
	PosEyeZ=positionZ;
	PosCentX=PosCentY=PosCentZ=0.0;


	up_down = true;

	camView.x	= positionX;
	camView.y	= positionY;
	camView.z	= positionZ;

	// punto a mirar 
	camAt.x		= 0.0f;
	camAt.y		= 0.0f;
	camAt.z		= 0.0f;

	camUp.x		= 0.0f;
	camUp.y		= 1.0f;
	camUp.z		= 0.0f;

	camAperture	=  60.0f * DEGREE_TO_RAD;
	camNear		=   0.5f;
	camFar		= 200.0f;
	
	SetFull(camJ,0,1,0);
	NormalizeR(camJ);
	DireccionByResta(camK,camAt,camView);
	CrossNormalize(camI,camJ,camK);

	camProjection = CAM_PARALLEL;
	aspectRatio   = 1.0f;
	fact_W=fact_H=1;
	SetDependentParametersCamera();
}
GL_Camara::~GL_Camara(void)
{
}
void GL_Camara::SetCamera( float viewX, float viewY, float viewZ,
			float atX,   float atY,   float atZ,
			float upX,   float upY,   float upZ )
{
	camView.x = viewX;
	camView.y = viewY;
	camView.z = viewZ;
	camAt.x = atX;
	camAt.y = atY;
	camAt.z = atZ;
	camUp.x = upX;
	camUp.y = upY;
	camUp.z = upZ;

	Resta(camK,camAt,camView);

	SetDependentParametersCamera();
}
void GL_Camara::SetParametrosHapticos(stVertex _h_Eye,stVertex _h_Center,stVertex _h_Up)
{
	if(!m_haptic_set)
		return;
	camView = _h_Eye;
	camAt = _h_Center;
	camUp = _h_Up;

	SetDependentParametersCamera();
}
void GL_Camara::Examinar(int x, int y)
{

	float rot_x, rot_y;
	rot_y = (float)(y - old_y);
	rot_x = (float)(old_x - x);
	Rotar(rot_x * DEGREE_TO_RAD, rot_y * DEGREE_TO_RAD );

	old_y = y;
	old_x = x;
}
void GL_Camara::MouseMotion(int x, int y)
{
	old_y = y;
	old_x = x;
}
void GL_Camara::SetDependentParametersCamera(void)
{

	if(up_down)SetFull(camUp,0.0, 1.0, 0.0);
	else SetFull(camUp,0.0, -1.0, 0.0);
}

void GL_Camara::SetGLCamera( void )
{
	float	 fovy;
	glViewport(0, 0, Width, Height);
	glMatrixMode( GL_PROJECTION );

	glLoadIdentity( );

	if( camProjection == CAM_CONIC ) 
	{
		fovy   = camAperture * RAD_TO_DEGREE;
		gluPerspective( fovy, aspectRatio, camNear, camFar );
	}
	if(camProjection == CAM_PARALLEL ) 
	{ 
		glOrtho(0,Width*fact_W,0,Height*fact_H,-3000,3000);
	}
	float P2[3]={0,1,0},P2s[3];
	float P1[3]={0,0,0},P1s[3];
	glPushMatrix();
		glLoadIdentity();
	
		gluLookAt(	camView.x, camView.y, camView.z, 
					camAt.x,   camAt.y,   camAt.z,
					camUp.x,   camUp.y,   camUp.z );
		glGetFloatv (GL_PROJECTION_MATRIX, look_matrix);
		InversaLU(look_matrix);

		MultMxV(P2s,m_proyection_invertida,P2);
		MultMxV(P1s,m_proyection_invertida,P1);

		SetFull(camJ,P2s[0]-P1s[0],P2s[1]-P1s[1],P2s[2]-P1s[2]);
		NormalizeR(camJ);
		DireccionByResta(camK,camAt,camView);
		CrossNormalize(camI,camK,camJ);
	glPopMatrix();

	glMultMatrixf(look_matrix);


	glMatrixMode( GL_MODELVIEW );	// *** GL_MODELVIEW ***
	glLoadIdentity();

	glGetIntegerv (GL_VIEWPORT, viewport);
	glGetFloatv (GL_MODELVIEW_MATRIX, modelview);
	glGetFloatv (GL_PROJECTION_MATRIX, projection);
	glClearColor(125/255.0f, 136/255.0f, 232/255.0f, 1.0f);	

}
void GL_Camara::GetMatrix(GLdouble *m, GLdouble *p, GLint *v)
{
	for (int i=0;i<16;i++)
	{
		p[i] =	projection[i]; 
		m[i] =	modelview[i];
	}
	for (int i=0;i<4;i++)
		v[i] =	viewport[i];
}
void GL_Camara::GetInvMatrix(float* m)
{
	for (int i=0;i<16;i++)
		m[i] =	m_proyection_invertida[i]; 
}

void GL_Camara::GetDirMatrix(float* m)
{
	for (int i=0;i<16;i++)
		m[i] =	look_matrix[i]; 
}

void GL_Camara::SetGLAspectRatioCamera( void )
{
	

	if( Height > 0 )
		aspectRatio = (float) Width / (float) Height;	// width/height
	else
		aspectRatio = 1.0f;

	SetDependentParametersCamera();

}
void GL_Camara::AvanceFreeCamera( float step  )
{
	stVertex va;
	Amplificar(va,step,camK);
	// Set V & A
	Suma(camView,camView,va);
	Suma(camAt,camAt,va);
	
	SetDependentParametersCamera();
}
void GL_Camara::YawCamera(float angle )
{
	float vIn[3];
	
	vIn[0]= camAt.x - camView.x;
	vIn[1]= camAt.y - camView.y;
	vIn[2]= camAt.z- camView.z;
	
	VectorRotY( vIn, angle );

	camAt.x = camView.x + vIn[0];
	camAt.y = camView.y + vIn[1];
	camAt.z = camView.z + vIn[2];

	SetDependentParametersCamera();
}
void GL_Camara::Rotar_Latitud(float inc )
{
	float vIn[3];
	
	vIn[0]= camView.x - camAt.x;
	vIn[1]= camView.y - camAt.y;
	vIn[2]= camView.z - camAt.z;
	
	VectorRotXZ( vIn, inc, TRUE );

	camView.x = camAt.x + vIn[0];
	camView.y = camAt.y + vIn[1];
	camView.z = camAt.z + vIn[2];

	SetDependentParametersCamera();
}
void GL_Camara::Rotar_Longitud(float inc )
{
	float vIn[3];	
	
	vIn[0]= camView.x - camAt.x;
	vIn[1]= camView.y - camAt.y;
	vIn[2]= camView.z - camAt.z;
	
	/*
	double dvOrig[3];
	double dvCenter[3];

	gluUnProject(camView.x,camView.y,camView.z,identity,projection,viewport,&dvOrig[0],&dvOrig[1],&dvOrig[2]);
	gluUnProject(camAt.x,camAt.y,camAt.z,identity,projection,viewport,&dvCenter[0],&dvCenter[1],&dvCenter[2]);
	vIn[0] = dvOrig[0] - dvCenter[0];
	vIn[1] = dvOrig[1] - dvCenter[1];
	vIn[2] = dvOrig[2] - dvCenter[2];
	*/
	VectorRotY( vIn, inc );
	/*
	dvOrig[0] = vIn[0] + dvCenter[0];
	dvOrig[1] = vIn[1] + dvCenter[1];
	dvOrig[2] = vIn[2] + dvCenter[2];
	gluProject(dvOrig[0],dvOrig[1],dvOrig[2],identity,projection,viewport,&dvCenter[0],&dvCenter[1],&dvCenter[2]);

	vIn[0] = dvCenter[0];
	vIn[1] = dvCenter[1];
	vIn[2] = dvCenter[2];
	*/

	camView.x = camAt.x + vIn[0];
	camView.z = camAt.z + vIn[2];

	SetDependentParametersCamera();
}

void GL_Camara::Rotar(float inc_x, float inc_y)
{
	float vIn[3];	
	
	vIn[0]= camView.x - camAt.x;
	vIn[1]= camView.y - camAt.y;
	vIn[2]= camView.z - camAt.z;
	
	VectorRot( vIn, inc_x, inc_y);

	camView.x = camAt.x + vIn[0];
	camView.y = camAt.y + vIn[1];
	camView.z = camAt.z + vIn[2];

	SetDependentParametersCamera();
}

void GL_Camara::SetOldXY(int x, int y)
{
	old_x=x;
	old_y=y;
}
void GL_Camara::Andar(int x, int y)
{
	float delta_x = (float)(x - old_x) / 10;
	float delta_y = (float)(y - old_y) / 10;
	stVertex temp;

	NormalizeR(camI);
	NormalizeR(camJ);

	if(delta_x!=0)
	{
		Amplificar(temp,-delta_x,camI);
		Suma(camView,camView,temp);
		Suma(camAt,camAt,temp);
	}
	if(delta_y!=0)
	{
		Amplificar(temp,delta_y,camJ);
		Suma(camView,camView,temp);
		Suma(camAt,camAt,temp);
	}
	//float rotacion_x, avance_y;
	//avance_y = (float)(y - old_y) / 10;
	//rotacion_x = (float)(old_x - x) * DEGREE_TO_RAD / 5;
	//YawCamera( rotacion_x );
	//AvanceFreeCamera( avance_y);
	old_y = y;
	old_x = x;
}
void GL_Camara::Zoom(int x, int y)
{
	float zoom;
	zoom = (float) ((y - old_y) * DEGREE_TO_RAD);
	old_y = y;
	switch(camMovimiento)
	{
		case CAM_EXAMINAR:
			if(camProjection==CAM_CONIC)
			{
				if (camAperture + zoom > (5 * DEGREE_TO_RAD) &&	camAperture + zoom < 175 * DEGREE_TO_RAD)
					camAperture=camAperture + zoom;
			}
			if(camProjection==CAM_PARALLEL)
			{
				if(zoom>0)
				{
					fact_W*=1.05;
					fact_H*=1.05;
				}
				if(zoom<0)
				{
					fact_W*=0.95;
					fact_H*=0.95;
				}

			}
			break;
	}

}
void GL_Camara::ZoomHaptic(int tipo)
{
	float zoom;
	switch(tipo)
	{
	case H_ZOOM_IN:
		zoom = 1;
		break;
	case H_ZOOM_OUT:
		zoom =-1;
		break;
	case H_ZOOM_NONE:
		return;
	}
	zoom = (float) (zoom * DEGREE_TO_RAD);
	if(camProjection==CAM_CONIC)
	{
		if (camAperture + zoom > (5 * DEGREE_TO_RAD) &&	camAperture + zoom < 175 * DEGREE_TO_RAD)
			camAperture=camAperture + zoom;
	}
	if(camProjection==CAM_PARALLEL)
	{
		if(zoom>0)
		{
			fact_W*=1.05;
			fact_H*=1.05;
		}
		if(zoom<0)
		{
			fact_W*=0.95;
			fact_H*=0.95;
		}
	}
}
void GL_Camara::ClickMouse(int x, int y)
{
	SetOldXY(x,y);
	switch(GetCamMovimiento())
	{
		case CAM_EXAMINAR:
			if (state == KEY_M_L_DOWN) 
			{
				m_Examinar=false;
				m_Zoom=true;
			}
			if (state == KEY_M_L_UP)
			{
				m_Examinar=true;
				m_Zoom=false;
			}
			break;
		case CAM_PASEAR:
			if (state == KEY_M_L_DOWN) 
			{
				m_MouseMotion=false;
				m_Andar=true;
			}
			if (state == KEY_M_L_UP) 
			{
				m_MouseMotion=true;
				m_Andar=false;
			}
			break;
	}
}
void GL_Camara::KeyBoard(int key)
{
	if(key==KEY_T_F1)
	{
		m_MouseMotion=true;
		m_Examinar=false;
		m_Andar=false;
		m_Zoom=false;
		m_Selection=true;
		m_camara_move=false;
		SetCamMovimiento(CAM_STOP);
	}
	else
	{
		if(key==KEY_T_F2)
		{
			m_Examinar=true;
			m_MouseMotion=false;
			m_Andar=false;
			m_Zoom=false;
			m_Selection=false;
			m_camara_move=true;
			SetCamMovimiento(CAM_EXAMINAR);
		}
		else
			if(key==KEY_T_F3)
			{
				m_MouseMotion=true;
				m_Examinar=false;
				m_Andar=false;
				m_Zoom=false;
				m_Selection=false;
				m_camara_move=true;
				SetCamMovimiento(CAM_PASEAR);
				SetDependentParametersCamera();
			}
			else
				if(key==KEY_T_HOME)
				{
					up_down = true;
					m_Selection=false;
					m_camara_move=true;
					SetCamAtXYZ(PosCentX,PosCentY,PosCentZ);
					SetCamViewXYZ(PosEyeX,PosEyeY,PosEyeZ);
					SetDependentParametersCamera();
				}
	}
}
void GL_Camara::MouseMove(int x, int y)
{
	if( m_MouseMotion) 
	{
		MouseMotion(x,y);
	}
	if( m_Examinar) 
	{
		Examinar(x,y);
	}
	if( m_Zoom) 
	{
		Zoom(x,y);
	}
	if( m_Andar) 
	{
		Andar(x,y);
	}
}

//=============================================================================
//=============================================================================
//=============================================================================
//=============================================================================
void GL_Camara::VectorRotY( float *vIn, float inc )
{
	float	 alpha;
	float	 modZX;
	float	 mod;

	//         __________________> X          
	//        |*          
	//        | *           
	//        |  *         
	//        |   *        
	//        |    *       
	//        |     *      
	//        |      *     
	//        | alpha *    
	//        |        *    
	//        v           
	//       Z      

	mod = MOD( vIn[0], vIn[1], vIn[2] );
	
	if( mod < VECTOR_EPSILON ) 
		return;
	
	vIn[0] = vIn[0] / mod;
	vIn[1] = vIn[1] / mod;
	vIn[2] = vIn[2] / mod;

	// si el vector es muy paralelo al eje "y" no haga nada
	/**
	if( fabs( vIn[1] ) > sin( PI_VALUE/2.0 - ANGLE_EPSILON ) ) 
	{
		vIn[0] = vIn[0] * mod;
		vIn[1] = vIn[1] * mod;
		vIn[2] = vIn[2] * mod;
		return;
	}
	/**/
	modZX = (float) sqrt( vIn[0]*vIn[0] + vIn[2]*vIn[2] );
	alpha = (float) acos( vIn[2] / modZX );

	if( vIn[0] < 0.0f ) 
		alpha = 2.0f * PI_VALUE - alpha;

//	if((vIn[0] < 0.0f && up_down)){
//		alpha = 2.0f * PI_VALUE - alpha;
//	}
//	if((vIn[0] > 0.0f && !up_down)){
//		alpha = 2.0f * PI_VALUE - alpha;
//	}

	alpha += inc;
	vIn[0] = (float) sin( alpha ) * modZX;
	vIn[2] = (float) cos( alpha ) * modZX;

	vIn[0] = vIn[0] * mod;
	vIn[1] = vIn[1] * mod;
	vIn[2] = vIn[2] * mod;

}

void GL_Camara::VectorRotXZ( float *vIn, float inc, int flagStop )
{
	float	 alpha, beta;
	float	 mod;
	float	 maxAngle = 90.0f * DEGREE_TO_RAD - ANGLE_EPSILON;

	// Plane that contains the vector and the "y" axis
	//
	//      Y          
	//        ^          
	//        |          
	//        |          
	//        |        *  
	//        |       *   
	//        |      *    
	//        |     *     
	//        |    *      
	//        |   *       
	//        |  *        
	//        | *  beta
	//        |*          
	//         ------------------> X-Z          
	//     
	mod = MOD( vIn[0], vIn[1], vIn[2] );
	if( mod < VECTOR_EPSILON ) return;
	vIn[0] = vIn[0] / mod;
	vIn[1] = vIn[1] / mod;
	vIn[2] = vIn[2] / mod;

	// si el vector es muy paralelo a "y"  no hacer nada
	/*
	if( fabs( vIn[1] ) > sin( maxAngle ) )
	{
		vIn[0] = vIn[0] * mod;
		vIn[1] = vIn[1] * mod;
		vIn[2] = vIn[2] * mod;
		return;
	}
	*/

	// 1 Compute alpha & beta
	alpha = (float) acos( vIn[2] / sqrt( vIn[0]*vIn[0] + vIn[2]*vIn[2] ) );

	// hypotenuse must be always 1.0 (because v is a unit vector)
	// first we measure beta from X-Z up to our vector
	// the result will be among -90 and +90
	beta = (float) asin( vIn[1] );

	if( vIn[0] < 0.0f ) 
		alpha = 2.0f * PI_VALUE - alpha;

//	if((vIn[0] < 0.0f && up_down)){
//		alpha = 2.0f * PI_VALUE - alpha;
//	}
//	if((vIn[0] > 0.0f && !up_down)){
//		alpha = 2.0f * PI_VALUE - alpha;
//	}

	//	beta += inc;

	if( fabs(vIn[1]) > sin(maxAngle-inc)){
		up_down = !up_down;
		beta -= 2*inc;
	}
	else{
		if(up_down){
			beta += inc;
		}
		else{
			beta -= inc;
		}
	}

//	if(beta > maxAngle)up_down = true;
//	else if(beta < -maxAngle)up_down = false;


	// 2 ConstantIncrement beta (two possibilities)
	/*
	if( flagStop ) {
		// when beta goes further than pi/2 or -pi/2 => stop avoiding a vertical position
		beta += inc;
		if( beta > maxAngle )		 beta =   maxAngle;
		else if( beta < - maxAngle ) beta = - maxAngle;
	}
	else {
		// to keep a constant rotation direction inc must be a positive value
		if( alpha > PI_VALUE )	beta -= inc;
		else					beta += inc;
	}
	*/
//	beta += inc;

	// 3 Compute new vector	
	vIn[0] = (float) cos( beta ) * (float) sin( alpha );
	vIn[1] = (float) sin( beta );
	vIn[2] = (float) cos( beta ) * (float) cos( alpha );

	vIn[0] = vIn[0] * mod;
	vIn[1] = vIn[1] * mod;
	vIn[2] = vIn[2] * mod;
}

void GL_Camara::VectorRot( float *vIn, float inc_x, float inc_y)
{
	float	 alpha, beta;
	float	 mod;

	// Plane that contains the vector and the "y" axis
	//
	//      Y          
	//        ^          
	//        |          
	//        |          
	//        |        *  
	//        |       *   
	//        |      *    
	//        |     *     
	//        |    *      
	//        |   *       
	//        |  *        
	//        | *  beta
	//        |*          
	//         ------------------> X-Z          
	//     
	mod = MOD( vIn[0], vIn[1], vIn[2] );
	if( mod < VECTOR_EPSILON ) return;
	vIn[0] = vIn[0] / mod;
	vIn[1] = vIn[1] / mod;
	vIn[2] = vIn[2] / mod;

	// 1 Compute alpha & beta
	alpha = acosf( vIn[2] / sqrtf( vIn[0]*vIn[0] + vIn[2]*vIn[2] ) );

	// hypotenuse must be always 1.0 (because v is a unit vector)
	// first we measure beta from X-Z up to our vector
	// the result will be among -90 and +90
	beta = asinf( vIn[1] );

	if( vIn[0] < 0.0f )alpha =  -alpha;

	beta += (up_down)?inc_y:-inc_y;
	if( fabs(beta) >= PI_VALUE/2.0 - ANGLE_EPSILON){
		up_down = !up_down;
		beta = (beta>0)?PI_VALUE/2.0 - 2*ANGLE_EPSILON:-(PI_VALUE/2.0 - 2*ANGLE_EPSILON);
		alpha += PI_VALUE;
	}
	alpha+=inc_x;

	// 3 Compute new vector	
	vIn[0] = cosf( beta ) * sinf( alpha );
	vIn[1] = sinf( beta );
	vIn[2] = cosf( beta ) * cosf( alpha );

	vIn[0] = vIn[0] * mod;
	vIn[1] = vIn[1] * mod;
	vIn[2] = vIn[2] * mod;
}

bool GL_Camara::InversaLU(float *m_origen)
{
	int filas,columnas;
	filas=columnas=4;


	int i,j,k;
	float m_origen_copy[16];
	float* b = new float[columnas];
	float factor,sum;
	for(int i=0;i<16;i++)
		m_origen_copy[i]=m_origen[i];
	
	for(k=0;k<columnas-1;k++)
	{
		for(i = k + 1; i < columnas; i++)
		{
			if(m_origen_copy[k*4+k] == 0)
			{
				for(int pi=0;pi<4;pi++)
				{
					for(int pj=0;pj<4;pj++)
						if(pi!=pj)
							m_proyection_invertida[pi*4+pj]=0.0;
						else
							m_proyection_invertida[pi*4+pj]=1.0;
				}
				return false;
			}
			factor = m_origen_copy[i*4+k]/m_origen_copy[k*4+k];
			m_origen_copy[i*4+k] = factor;
			if(factor)
			{
				for(j = k + 1; j < columnas; j++)
				{
					m_origen_copy[i*4+j] -= factor*m_origen_copy[k*4+j];
				}
			}
		}
	}
	for(j=0;j<columnas;j++)
	{
		for (i = 0; i < columnas; i++) 
		{
			b[i] = (i==j)?1.0f:0.0f;
		}

		for(i = 1;i<columnas;i++)
		{                    
			sum=b[i];
			for(k=0;k<i;k++)
				sum=sum-m_origen_copy[i*4+k]*b[k];
			b[i]=sum;
		}

		m_proyection_invertida[(columnas-1)*4+j]=b[columnas-1]/m_origen_copy[(columnas-1)*4+(columnas-1)];
		
		for(i=columnas;i>0;i--)
		{
			sum=0;
			for(k = i; k < columnas; k++)
				sum=sum + m_origen_copy[(i-1)*4+k]*m_proyection_invertida[k*4+j];
			m_proyection_invertida[(i-1)*4+j]=(b[i-1]-sum)/m_origen_copy[(i-1)*4+(i-1)];
		}
	}
	delete b;

	return true;
}

void GL_Camara::glDrawViewPort(void)
{
	GLfloat light_pos[] = { 0.0, 0.0, 1.0, 0.0 };
	GLdouble inverse[16],modelv[16],proyect[16];
	double length;
	stVertex temp;
	
	length = DireccionByResta(temp,camView,camAt);

	for(int i=0;i<16;i++)
	{
		modelv[i]=modelview[i];
		proyect[i]=projection[i];
	}
    
	invert(modelv, inverse);
	glDisable(GL_LIGHTING);
	glPushMatrix();
    
		glMultMatrixd(inverse);
	    
		//glLightfv(GL_LIGHT0, GL_POSITION, light_pos);
	    
		/* draw the axis and eye vector */
		//glPushMatrix();
			//glColor3ub(0, 0, 255);
			//glBegin(GL_LINE_STRIP);
			//glVertex3f(0.0, 0.0, 0.0);
			//glVertex3f(0.0, 0.0, -1.0*length);
			//glVertex3f(0.1, 0.0, -0.9*length);
			//glVertex3f(-0.1, 0.0, -0.9*length);
			//glVertex3f(0.0, 0.0, -1.0*length);
			//glVertex3f(0.0, 0.1, -0.9*length);
			//glVertex3f(0.0, -0.1, -0.9*length);
			//glVertex3f(0.0, 0.0, -1.0*length);
			//glEnd();
			//glColor3ub(255, 255, 0);
			//glRasterPos3f(0.0, 0.0, -1.1*length);
			//glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, 'e');
			//glColor3ub(255, 0, 0);
			//glScalef(0.4, 0.4, 0.4);
			//drawaxes();
		//glPopMatrix();
    
		invert(proyect, inverse);
		glMultMatrixd(inverse);
	    
		/* draw the viewing frustum */
		glColor3f(0.2, 0.2, 0.2);
		//glBegin(GL_QUADS);
		//glVertex3i(1, 1, 1);
		//glVertex3i(-1, 1, 1);
		//glVertex3i(-1, -1, 1);
		//glVertex3i(1, -1, 1);
		//glEnd();
	    
		//glColor3ub(128, 196, 128);
		//glBegin(GL_LINES);
		//glVertex3i(1, 1, -1);
		//glVertex3i(1, 1, 1);
		//glVertex3i(-1, 1, -1);
		//glVertex3i(-1, 1, 1);
		//glVertex3i(-1, -1, -1);
		//glVertex3i(-1, -1, 1);
		//glVertex3i(1, -1, -1);
		//glVertex3i(1, -1, 1);
		//glEnd();
	 //   
		GLUquadric *quadric = gluNewQuadric();  

		glEnable(GL_BLEND);
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
		glColor4f(0.2, 0.2, 0.4, 0.5);

    ////Draw the cone
    //
    //    gl.glTranslatef(1.5f, 0.65f, 0.0f);
    //    gl.glRotatef(-90.0f, 1.0f, 0.0f, 0.0f);
    //    gl.glRotatef(cdRot, 0.0f, 0.0f, 1.0f);
    //   
    //    glu.gluQuadricDrawStyle(quadric, render1);
        gluCylinder(quadric, 1.0, 1.0, 1.0f, 20, 20);
    

		//glBegin(GL_QUADS);
		//glVertex3i(1, 1, -1);
		//glVertex3i(-1, 1, -1);
		//glVertex3i(-1, -1, -1);
		//glVertex3i(1, -1, -1);
		//glEnd();
		glDisable(GL_BLEND);
    
    glPopMatrix();
	glEnable(GL_LIGHTING);

}
GLboolean GL_Camara::invert(GLdouble src[16], GLdouble inverse[16])
{
    double t;
    int i, j, k, swap;
    GLdouble tmp[4][4];
    
    identity(inverse);
    
    for (i = 0; i < 4; i++) {
        for (j = 0; j < 4; j++) {
            tmp[i][j] = src[i*4+j];
        }
    }
    
    for (i = 0; i < 4; i++) {
        /* look for largest element in column. */
        swap = i;
        for (j = i + 1; j < 4; j++) {
            if (fabs(tmp[j][i]) > fabs(tmp[i][i])) {
                swap = j;
            }
        }
        
        if (swap != i) {
            /* swap rows. */
            for (k = 0; k < 4; k++) {
                t = tmp[i][k];
                tmp[i][k] = tmp[swap][k];
                tmp[swap][k] = t;
                
                t = inverse[i*4+k];
                inverse[i*4+k] = inverse[swap*4+k];
                inverse[swap*4+k] = t;
            }
        }
        
        if (tmp[i][i] == 0) {
        /* no non-zero pivot.  the matrix is singular, which
           shouldn't happen.  This means the user gave us a bad
            matrix. */
            return GL_FALSE;
        }
        
        t = tmp[i][i];
        for (k = 0; k < 4; k++) {
            tmp[i][k] /= t;
            inverse[i*4+k] /= t;
        }
        for (j = 0; j < 4; j++) {
            if (j != i) {
                t = tmp[j][i];
                for (k = 0; k < 4; k++) {
                    tmp[j][k] -= tmp[i][k]*t;
                    inverse[j*4+k] -= inverse[i*4+k]*t;
                }
            }
        }
    }
    return GL_TRUE;
}
void GL_Camara::identity(GLdouble m[16])
{
    m[0+4*0] = 1; m[0+4*1] = 0; m[0+4*2] = 0; m[0+4*3] = 0;
    m[1+4*0] = 0; m[1+4*1] = 1; m[1+4*2] = 0; m[1+4*3] = 0;
    m[2+4*0] = 0; m[2+4*1] = 0; m[2+4*2] = 1; m[2+4*3] = 0;
    m[3+4*0] = 0; m[3+4*1] = 0; m[3+4*2] = 0; m[3+4*3] = 1;
}

void GL_Camara::MultMxV(float *_C, float *A, float *_B)
{
	int i,k;
	float sum = 0.0;
	float C[4]={0,0,0,1};
	float B[4]={_B[0],_B[1],_B[2],1};

	for(i=0; i<4; i++)
	{
		sum = 0.0;
		for(k=0; k<4; k++)
			sum += A[k*4+i] * B[k];

		C[i] = sum;
	}
	_C[0]=C[0];
	_C[1]=C[1];
	_C[2]=C[2];
}