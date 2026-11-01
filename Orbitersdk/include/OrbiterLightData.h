// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_LIGHT_DATA_H
#define ORBITER_LIGHT_DATA_H
#include "OrbiterGeometry.h"
#include "OrbiterHandles.h"
#include "OrbiterMeshData.h"

class OAPIFUNC LightEmitter {
public:
	enum TYPE {
		LT_NONE, LT_POINT, LT_SPOT, LT_DIRECTIONAL
	};

	enum VISIBILITY {
		VIS_EXTERNAL=1, VIS_COCKPIT=2, VIS_ALWAYS=3
	};

	/**
	 * \brief Create a light source with default parameters.
	 * \note Creates a light source with white spectrum for diffuse, specular
	 *   and emissive colour components.
	 * \note Intensity is set to 1, position (for point source objects) is set to (0,0,0)
	 *   and direction (for spot and directional lights) is set to (0,0,1). To change
	 *   these, use \ref SetPosition, \ref SetPositionRef, \ref SetDirection,
	 *   \ref SetDirectionRef, \ref SetIntensity, \ref SetIntensityRef
	 */
	LightEmitter ();

	/**
	 * \brief Create a light source with specific colour parameters.
	 * \param diffuse light source's contribution to lit objects' diffuse colour component
	 * \param specular light source's contribution to lit objects' specular colour component
	 * \param ambient light source's contribution to lit objects' ambient colour component
	 * \note Intensity is set to 1, position (for point source objects) is set to (0,0,0)
	 *   and direction (for spot and directional lights) is set to (0,0,1). To change
	 *   these, use \ref SetPosition, \ref SetPositionRef, \ref SetIntensity, \ref SetIntensityRef
	 */
	LightEmitter (COLOUR4 diffuse, COLOUR4 specular, COLOUR4 ambient);

	/**
	 * \brief Returns the light source type.
	 */
	TYPE GetType() const { return ltype; }

	/**
	 * \brief Returns the light visibility mode
	 * \return visibility mode
	 */
	VISIBILITY GetVisibility() const { return visibility; }

	/**
	 * \brief Set the light visibility mode
	 * \param vis visibility mode
	 */
	void SetVisibility (VISIBILITY vis) { visibility = vis; }

	const COLOUR4 &GetDiffuseColour() const { return col_diff; }
	const COLOUR4 &GetSpecularColour() const { return col_spec; }
	const COLOUR4 &GetAmbientColour() const { return col_ambi; }

	/**
	 * \brief Activate or deactivate the light source
	 * \param act if \e true, activates the light source. Otherwise, deactivates
	 *   the light source
	 * \sa IsActive
	 */
	void Activate (bool act);

	/**
	 * \brief Returns activation status of light source
	 * \return \e true if source is active, \e false otherwise.
	 * \sa Activate
	 */
	bool IsActive () const;

	/**
	 * \brief Set light source position.
	 * \param p new position [<b>m</b>] (in object or global coordinates)
	 * \note The source position is only relevant for point and spot lights. It is
	 *   ignored for directional lights
	 * \note If the source is attached to an object (see \ref Attach) the position is
	 *   interpreted in the local object coordinates. Otherwise, the position is
	 *   taken to be in global coordinates.
	 * \note After a displacement of the vessel's centre of mass (see \ref VESSEL::ShiftCG),
	 *   all light sources that define their position explicitly (via SetPosition) are
	 *   updated automatically. Light sources with implicit position definition (via
	 *   \ref SetPositionRef) must update their positions themselves.
	 * \sa GetPosition, SetPositionRef, GetPositionRef
	 */
	void SetPosition (const VECTOR3 &p);

	/**
	 * \brief Returns the current source position.
	 * \return Current source position [<b>m</b>]
	 * \note The source position is only relevant for point and spot lights. It is
	 *   ignored for directional lights
	 * \note If the source is attached to an object (see \ref Attach) the returned
	 *   vector is the source position in local object coordinates. Otherwise, the
	 *   returned vector is the global source position.
	 * \sa SetPosition, SetPositionRef, GetPositionRef
	 */
	inline VECTOR3 GetPosition () const { return *pos; }

	/**
	 * \brief Set the reference pointer to the light source position.
	 * \param p pointer to vector defining the source position
	 * \note This method links the position of the light source to an externally
	 *   defined vector. By modifying the vector elements, the light source can
	 *   be re-positioned instantly.
	 * \note The vector variable pointed to by \a p must remain valid for the
	 *   lifetime of the light source.
	 * \note The source position is only relevant for point and spot lights. It is
	 *   ignored for directional lights
	 * \sa SetPosition, GetPosition, GetPositionRef
	 */
	void SetPositionRef (const VECTOR3 *p);

	/**
	 * \brief Returns a pointer to the position reference variable.
	 * \return Pointer to the variable defining the light source position
	 * \note If the position is defined explicitly (see \ref SetPosition),
	 *   this method simply returns a pointer to the lpos member variable.
	 *   Otherwise, is returns the pointer specified in \ref SetPositionRef.
	 * \sa SetPosition, SetPositionRef, GetPosition
	 */
	const VECTOR3 *GetPositionRef () const;

	/**
	 * \brief Adds an offset to the explicit position definition of the source.
	 * \param ofs offset vector in local vessel coordinates
	 * \note This method has only an effect for light sources whose positions are
	 *   defined explicitly (via \ref SetPosition). If the source position is defined
	 *   implicitly (via \ref SetPositionRef), this method has no effect. Modules that
	 *   define their light source positions via implicit references must keep the
	 *   positions up to date themselves (e.g. reacting to shifts in the centre of gravity).
	 * \sa SetPosition, SetPositionRef, VESSEL::ShiftCG
	 */
	void ShiftExplicitPosition (const VECTOR3 &ofs);

	/**
	 * \brief Set light source direction.
	 * \param p new direction (in object or global coordinates)
	 * \note The vector argument should be normalised to length 1.
	 * \note The source direction is only relevant for spot and directional lights.
	 *   It is ignored for point lights.
	 * \note If the source is attached to an object (see \ref Attach) the direction is
	 *   interpreted in the local object coordinates. Otherwise, the direction is
	 *   taken to be in global coordinates.
	 * \sa GetDirection, SetDirectionRef, GetDirectionRef
	 */
	void SetDirection (const VECTOR3 &d);

	/**
	 * \brief Returns the current source direction.
	 * \return Current source direction.
	 * \note The source direction is only relevant for spot and directional lights.
	 *   It is ignored for point lights.
	 * \note If the source is attached to an object (see \ref Attach) the returned
	 *   vector is the source direction in local object coordinates. Otherwise, the
	 *   returned vector is the global source direction.
	 * \sa SetDirection, SetDirectionRef, GetDirectionRef
	 */
	VECTOR3 GetDirection () const;

	/**
	 * \brief Set the reference pointer to the light source direction.
	 * \param d pointer to vector defining the source direction
	 * \note This method links the direction of the light source to an externally
	 *   defined vector. By modifying the vector elements, the light source can
	 *   be re-directed instantly.
	 * \note The vector variable pointed to by \a d must remain valid for the
	 *   lifetime of the light source.
	 * \note The source direction is only relevant for spot and directional lights.
	 *   It is ignored for point lights
	 * \sa SetDirection, GetDirection, GetDirectionRef
	 */
	void SetDirectionRef (const VECTOR3 *d);

	/**
	 * \brief Returns a pointer to the direction reference variable.
	 * \return Pointer to the variable defining the light source direction
	 * \note If the direction is defined explicitly (see \ref SetDirection),
	 *   this method simply returns a pointer to the ldir member variable.
	 *   Otherwise, is returns the pointer specified in \ref SetDirectionRef.
	 * \sa SetDirection, SetDirectionRef, GetDirection
	 */
	const VECTOR3 *GetDirectionRef () const;

	/**
	 * \brief Returns the handle of the object the light source is attached to.
	 * \return Object handle, or NULL if not attached
	 */
	const OBJHANDLE GetObjectHandle () const { return hRef; }

	void SetIntensity (double in);
	double GetIntensity () const;
	void SetIntensityRef (double *pin);
	const double *GetIntensityRef () const;

protected:
	OBJHANDLE Attach (OBJHANDLE hObj);
	OBJHANDLE Detach ();

	TYPE ltype;
	VISIBILITY visibility;
	OBJHANDLE hRef;
	bool active;
	COLOUR4 col_diff;
	COLOUR4 col_spec;
	COLOUR4 col_ambi;
	const double *intens;
	double lintens;
	const VECTOR3 *pos;
	const VECTOR3 *dir;
	VECTOR3 lpos;
	VECTOR3 ldir;
};

/**
 * \brief Class for isotropic point light source
 */
class OAPIFUNC PointLight: public LightEmitter {
public:
	/**
	 * \brief Creates a white isotropic point light.
	 * \param hObj handle of object the point light is attached to
	 * \param _pos light position in local object coordinates [<b>m</b>]
	 * \param _range point light range [m]
	 * \param att0 light attenuation parameters
	 * \param att1 light attenuation parameters
	 * \param att2 light attenuation parameters
	 */
	PointLight (OBJHANDLE hObj, const VECTOR3 &_pos, double _range, double att0, double att1, double att2);

	/**
	 * \brief Creates a coloured isotropic point light.
	 * \param hObj handle of object the point light is attached to
	 * \param _pos point light position in local object coordinates [<b>m</b>]
	 * \param _range spotlight range [m]
	 * \param att0 light attenuation parameters
	 * \param att1 light attenuation parameters
	 * \param att2 light attenuation parameters
	 * \param diffuse light source's contribution to lit objects' diffuse colour component
	 * \param specular light source's contribution to lit objects' specular colour component
	 * \param ambient light source's contribution to lit objects' ambient colour component
	 */
	PointLight (OBJHANDLE hObj, const VECTOR3 &_pos, double _range, double att0, double att1, double att2, COLOUR4 diffuse, COLOUR4 specular, COLOUR4 ambient);

	/**
	 * \brief Returns the light source range.
	 * \return Light source range [m]
	 */
	double GetRange() const { return range; }

	/**
	 * \brief Set the light source range.
	 * \param _range new light source range [m]
	 * \note When changing the range, the attenuation factors usually should be adjusted
	 *   accordingly, to avoid sharp cutoff edges or large areas of negligible intensity.
	 */
	void SetRange (double _range);

	/**
	 * \brief Returns a pointer to attenuation coefficients.
	 * \return Pointer to array of 3 attenuation coefficients.
	 * \note The attenuation coefficients define the fractional light intensity I/I0 as
	 *   a function of distance d:
	 *   \f[ \frac{I}{I_0} = \frac{1}{\mathrm{att}_0 + d \mathrm{att}_1 + d^2 \mathrm{att}_2} \f]
	 */
	const double *GetAttenuation() const { return att; }

	/**
	 * \brief Set the attenuation coefficients.
	 * \param att0 attenuation coefficient
	 * \param att1 attenuation coefficient
	 * \param att2 attenuation coefficient
	 * \note The attenuation coefficients define the fractional light intensity I/I0 as
	 *   a function of distance d:
	 *   \f[ \frac{I}{I_0} = \frac{1}{\mathrm{att}_0 + d \mathrm{att}_1 + d^2 \mathrm{att}_2} \f]
	 */
	void SetAttenuation (double att0, double att1, double att2);

protected:
	double range;
	double att[3];
};

/**
 * \brief Class for directed spot light sources
 */
class OAPIFUNC SpotLight: public PointLight {
public:
	/**
	 * \brief Creates a white spotlight.
	 * \param hObj handle of object the spotlight is attached to
	 * \param _pos spotlight position in local object coordinates [<b>m</b>]
	 * \param _dir spotlight direction in local object coordinates
	 * \param _range spotlight range [m]
	 * \param att0 light attenuation parameters
	 * \param att1 light attenuation parameters
	 * \param att2 light attenuation parameters
	 * \param _umbra angular aperture of inner (maximum intensity) cone [rad]
	 * \param _penumbra angular aperture of outer (zero intensity) cone [rad]
	 * \note Direction vector \a _dir must be normalised to length 1.
	 * \note 0 < _umbra <= penumbra <= pi is reqired.
	 * \note The intensity falloff between _umbra and _penumbra is linear from
	 *   maximum intensity to zero.
	 */
	SpotLight (OBJHANDLE hObj, const VECTOR3 &_pos, const VECTOR3 &_dir, double _range, double att0, double att1, double att2, double _umbra, double _penumbra);

	/**
	 * \brief Creates a coloured spotlight.
	 * \param hObj handle of object the spotlight is attached to
	 * \param _pos spotlight position in local object coordinates [<b>m</b>]
	 * \param _dir spotlight direction in local object coordinates
	 * \param _range spotlight range [m]
	 * \param att0 light attenuation parameters
	 * \param att1 light attenuation parameters
	 * \param att2 light attenuation parameters
	 * \param _umbra angular aperture of inner (maximum intensity) cone [rad]
	 * \param _penumbra angular aperture of outer (zero intensity) cone [rad]
	 * \param diffuse light source's contribution to lit objects' diffuse colour component
	 * \param specular light source's contribution to lit objects' specular colour component
	 * \param ambient light source's contribution to lit objects' ambient colour component
	 * \note Direction vector \a _dir must be normalised to length 1.
	 * \note 0 < _umbra <= penumbra <= pi is reqired.
	 * \note The intensity falloff between _umbra and _penumbra is linear from
	 *   maximum intensity to zero.
	 */
	SpotLight (OBJHANDLE hObj, const VECTOR3 &_pos, const VECTOR3 &_dir, double _range, double att0, double att1, double att2, double _umbra, double _penumbra, COLOUR4 diffuse, COLOUR4 specular, COLOUR4 ambient);

	/**
	 * \brief Returns the angular aperture of inner (maximum intensity) cone.
	 * \return Aperture of inner spotlight cone [rad]
	 * \sa GetPenumbra
	 */
	double GetUmbra() const { return umbra; }

	/**
	 * \brief Returns the angular aperture of outer (zero intensity) cone.
	 * \return Aperture of outer spotlight cone [rad]
	 * \sa GetUmbra
	 */
	double GetPenumbra() const { return penumbra; }

	/**
	 * \brief Set the spotlight cone geometry.
	 * \param _umbra angular aperture of inner (maximum intensity) cone [rad]
	 * \param _penumbra angular aperture of outer (zero intensity) cone [rad]
	 */
	void SetAperture (double _umbra, double _penumbra);

protected:
	double umbra;
	double penumbra;
};
#endif
